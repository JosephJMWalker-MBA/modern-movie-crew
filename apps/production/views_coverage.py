from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.characters.models import Character
from apps.production.models import (
    CoveragePlan,
    ScriptDocument,
    ScriptSegment,
    ScriptVersion,
    ShotDefinition,
)
from apps.projects.models import Department, Membership, Project
from services.shot_planning_services import (
    create_coverage_plan_with_shots,
    create_task_from_shot,
    detect_editorial_completeness_warnings,
    generate_coverage_plan_suggestions,
    waive_editorial_warning,
)


@login_required
def create_coverage_plan_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    doc = project.script_documents.order_by("-created_at").first()
    latest_version = doc.versions.first() if doc else None

    if not latest_version:
        messages.error(request, "Please import a project script before creating a coverage plan.")
        return redirect("script_workspace", slug=project.slug)

    segments = list(latest_version.segments.order_by("segment_number"))

    if request.method == "POST":
        start_seg_id = request.POST.get("start_segment_id")
        end_seg_id = request.POST.get("end_segment_id")
        title = request.POST.get("title", "").strip() or "Passage Coverage Plan"
        editorial_strategy = request.POST.get("editorial_strategy", "").strip()

        start_seg = get_object_or_404(ScriptSegment, pk=start_seg_id, script_version=latest_version)
        end_seg = get_object_or_404(ScriptSegment, pk=end_seg_id, script_version=latest_version)

        # Generate deterministic suggestions or use custom template
        suggestions = generate_coverage_plan_suggestions(
            script_version=latest_version,
            start_segment=start_seg,
            end_segment=end_seg,
        )

        try:
            plan = create_coverage_plan_with_shots(
                project=project,
                actor_membership=actor_membership,
                script_version=latest_version,
                start_segment=start_seg,
                end_segment=end_seg,
                title=title,
                shot_specs=suggestions,
                editorial_strategy=editorial_strategy,
            )
            messages.success(request, f"Coverage Plan '{plan.title}' created with {plan.shots.count()} shots!")
            return redirect("coverage_plan_detail", slug=project.slug, plan_id=plan.id)
        except Exception as e:
            messages.error(request, str(e))

    return render(
        request,
        "production/create_coverage_plan.html",
        {
            "project": project,
            "latest_version": latest_version,
            "segments": segments,
        },
    )


@login_required
def coverage_plan_detail_view(request, slug, plan_id):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    plan = get_object_or_404(CoveragePlan, pk=plan_id, project=project)
    shots = plan.shots.select_related("character", "created_by").prefetch_related("task_links__task").order_by("sequence_order")

    warnings = detect_editorial_completeness_warnings(coverage_plan=plan)
    waivers = plan.warning_waivers.select_related("waived_by").all()

    departments = project.departments.all()
    characters = project.characters.all()

    return render(
        request,
        "production/coverage_plan_detail.html",
        {
            "project": project,
            "plan": plan,
            "shots": shots,
            "warnings": warnings,
            "waivers": waivers,
            "departments": departments,
            "characters": characters,
            "actor_membership": actor_membership,
        },
    )


@login_required
def create_task_from_shot_view(request, slug, shot_id):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    shot = get_object_or_404(ShotDefinition, pk=shot_id, coverage_plan__project=project)

    if request.method == "POST":
        dept_id = request.POST.get("department_id")
        task_type = request.POST.get("task_type", "video")
        code = request.POST.get("code", "").strip()
        title = request.POST.get("title", "").strip()

        department = get_object_or_404(Department, pk=dept_id, project=project)

        try:
            task = create_task_from_shot(
                shot=shot,
                actor_membership=actor_membership,
                department=department,
                task_type=task_type,
                code=code,
                title=title,
            )
            messages.success(request, f"Production Task {task.code} created for Shot {shot.shot_code}!")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("coverage_plan_detail", slug=project.slug, plan_id=shot.coverage_plan.id)


@login_required
def waive_warning_view(request, slug, plan_id):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    plan = get_object_or_404(CoveragePlan, pk=plan_id, project=project)

    if request.method == "POST":
        warning_code = request.POST.get("warning_code", "").strip()
        reason = request.POST.get("reason", "").strip()

        if not reason:
            messages.error(request, "Director must provide an explicit rationale to waive a completeness warning.")
            return redirect("coverage_plan_detail", slug=project.slug, plan_id=plan.id)

        try:
            waiver = waive_editorial_warning(
                coverage_plan=plan,
                warning_code=warning_code,
                reason=reason,
                actor_membership=actor_membership,
            )
            messages.success(request, f"Warning '{warning_code}' waived successfully.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("coverage_plan_detail", slug=project.slug, plan_id=plan.id)
