from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.production.models import ProductionTask, TaskClaim
from apps.projects.models import (
    Department,
    Membership,
    ProductionRole,
    Project,
    ProjectInviteToken,
)
from apps.submissions.models import CanonicalSelection, Submission
from services.invite_services import (
    accept_project_invite,
    create_project_invite,
    revoke_project_invite,
)
from services.matching_services import find_eligible_open_tasks_for_contributor
from services.project_services import add_crew_member_with_role, create_project_with_defaults


@login_required
def create_project_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        synopsis = request.POST.get("synopsis", "")

        try:
            project = create_project_with_defaults(
                creator_user=request.user, name=name, synopsis=synopsis
            )
            messages.success(request, f"Project '{name}' created successfully!")
            return redirect("production_room", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "projects/create_project.html")


@login_required
def project_detail_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    memberships = project.memberships.select_related("user").all()
    departments = project.departments.prefetch_related("roles").all()
    invites = project.invite_tokens.all()

    user_membership = memberships.filter(user=request.user).first()

    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "memberships": memberships,
            "departments": departments,
            "user_membership": user_membership,
            "invites": invites,
        },
    )


@login_required
def add_crew_member_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        credited_name = request.POST.get("credited_name")
        role_id = request.POST.get("role_id")
        role = get_object_or_404(ProductionRole, pk=role_id, project=project)

        try:
            add_crew_member_with_role(
                project=project,
                actor_membership=actor_membership,
                target_user=request.user,
                credited_name=credited_name,
                role=role,
            )
            messages.success(request, f"Crew member '{credited_name}' added as {role.name}!")
            return redirect("project_detail", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    roles = ProductionRole.objects.filter(project=project)
    return render(request, "projects/add_crew.html", {"project": project, "roles": roles})


@login_required
def production_room_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    user_membership = get_object_or_404(Membership, project=project, user=request.user)

    all_tasks = project.tasks.all()
    total_tasks = all_tasks.count()
    satisfied_tasks = all_tasks.filter(status=ProductionTask.Status.SATISFIED).count()
    progress_percent = int((satisfied_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    open_tasks = all_tasks.filter(status=ProductionTask.Status.OPEN)
    claimed_claims = TaskClaim.objects.filter(task__project=project, status=TaskClaim.Status.ACTIVE)
    awaiting_reviews = Submission.objects.filter(task__project=project, status=Submission.Status.IN_REVIEW)
    revision_requests = Submission.objects.filter(task__project=project, status=Submission.Status.REVISION_REQUESTED)
    recent_canonicals = CanonicalSelection.objects.filter(task__project=project, retired_at__isnull=True)[:5]

    # Pagination for open tasks
    paginator = Paginator(open_tasks, 10)
    page_number = request.GET.get("page", 1)
    open_tasks_page = paginator.get_page(page_number)

    return render(
        request,
        "projects/production_room.html",
        {
            "project": project,
            "user_membership": user_membership,
            "total_tasks": total_tasks,
            "satisfied_tasks": satisfied_tasks,
            "progress_percent": progress_percent,
            "open_tasks_page": open_tasks_page,
            "claimed_claims": claimed_claims,
            "awaiting_reviews": awaiting_reviews,
            "revision_requests": revision_requests,
            "recent_canonicals": recent_canonicals,
        },
    )


@login_required
def create_invite_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        role_id = request.POST.get("role_id")
        duration_days = int(request.POST.get("duration_days", 7))
        max_uses = int(request.POST.get("max_uses", 5))

        default_role = get_object_or_404(ProductionRole, pk=role_id, project=project)

        try:
            invite = create_project_invite(
                project=project,
                actor_membership=actor_membership,
                default_role=default_role,
                duration_days=duration_days,
                max_uses=max_uses,
            )
            messages.success(request, f"Invite link created for role {default_role.name}!")
            return redirect("project_detail", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    roles = ProductionRole.objects.filter(
        project=project, can_accept_final_assets=False, can_manage_credits=False, can_assign_tasks=False
    )
    return render(request, "projects/create_invite.html", {"project": project, "roles": roles})


@login_required
def revoke_invite_view(request, slug, invite_id):
    project = get_object_or_404(Project, slug=slug)
    invite = get_object_or_404(ProjectInviteToken, pk=invite_id, project=project)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    try:
        revoke_project_invite(invite_token=invite, actor_membership=actor_membership)
        messages.success(request, "Invite link revoked!")
    except Exception as e:
        messages.error(request, str(e))

    return redirect("project_detail", slug=project.slug)


@login_required
def accept_invite_view(request, token_str):
    invite = get_object_or_404(ProjectInviteToken, token=token_str)

    if request.method == "POST":
        credited_name = request.POST.get("credited_name", "")

        try:
            membership = accept_project_invite(
                token_str=token_str, user=request.user, credited_name=credited_name
            )
            messages.success(request, f"Welcome to {membership.project.name}!")
            return redirect("production_room", slug=membership.project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "projects/accept_invite.html", {"invite": invite})


@login_required
def spare_gen_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    user_membership = get_object_or_404(Membership, project=project, user=request.user)

    asset_type = request.GET.get("asset_type", "")
    dept_id = request.GET.get("department_id", "")
    claimed_filter = request.GET.get("claimed", "all")

    asset_types = [asset_type] if asset_type else None
    department_id = int(dept_id) if dept_id else None

    # NON-MUTATING QUERY
    eligible_tasks = find_eligible_open_tasks_for_contributor(
        membership=user_membership,
        asset_types=asset_types,
        department_id=department_id,
        claimed_filter=claimed_filter,
    )

    paginator = Paginator(eligible_tasks, 12)
    page_number = request.GET.get("page", 1)
    tasks_page = paginator.get_page(page_number)

    departments = project.departments.all()

    return render(
        request,
        "projects/spare_gen.html",
        {
            "project": project,
            "user_membership": user_membership,
            "tasks_page": tasks_page,
            "departments": departments,
            "selected_asset_type": asset_type,
            "selected_dept": dept_id,
            "selected_claimed": claimed_filter,
        },
    )


@login_required
def edit_profile_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    user_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        user_membership.credited_name = request.POST.get("credited_name", user_membership.credited_name)
        user_membership.public_handle = request.POST.get("public_handle", "")
        tools = request.POST.get("available_tools", "")
        asset_types = request.POST.get("supported_asset_types", "")

        user_membership.available_tools = [t.strip() for t in tools.split(",") if t.strip()]
        user_membership.supported_asset_types = [a.strip() for a in asset_types.split(",") if a.strip()]
        user_membership.save()

        messages.success(request, "Contributor profile updated!")
        return redirect("production_room", slug=project.slug)

    return render(
        request,
        "projects/edit_profile.html",
        {"project": project, "membership": user_membership},
    )
