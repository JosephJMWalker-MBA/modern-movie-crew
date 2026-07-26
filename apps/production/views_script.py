from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.characters.models import Character
from apps.production.models import (
    PacketSection,
    ProductionTask,
    ScriptCharacterSuggestion,
    ScriptDocument,
    ScriptSegment,
    ScriptVersion,
    TaskScriptLink,
)
from apps.projects.models import Department, Membership, Project
from services.character_discovery_services import (
    confirm_character_suggestion,
    merge_character_alias,
    reject_character_suggestion,
)
from services.production_matrix_services import get_production_planning_matrix
from services.script_services import create_task_from_script_selection, import_script_document


@login_required
def script_import_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip() or "Project Script"
        description = request.POST.get("description", "").strip()
        raw_text = request.POST.get("raw_text", "").strip()

        uploaded_file = request.FILES.get("script_file")
        if uploaded_file:
            try:
                raw_text = uploaded_file.read().decode("utf-8")
            except Exception as e:
                messages.error(request, f"Could not read uploaded script file: {str(e)}")
                return render(request, "production/script_import.html", {"project": project})

        if not raw_text:
            messages.error(request, "Please paste raw screenplay text or upload a valid .txt/.md script file.")
            return render(request, "production/script_import.html", {"project": project})

        try:
            version = import_script_document(
                project=project,
                title=title,
                raw_text=raw_text,
                creator_membership=actor_membership,
                description=description,
            )
            messages.success(request, f"Script '{title}' imported successfully with {version.segments.count()} segments!")
            return redirect("script_workspace", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "production/script_import.html", {"project": project})


@login_required
def script_workspace_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    doc = project.script_documents.order_by("-created_at").first()
    latest_version = doc.versions.first() if doc else None

    # Handle character suggestion POST actions
    if request.method == "POST" and "action" in request.POST:
        action = request.POST.get("action")
        sug_id = request.POST.get("suggestion_id")
        suggestion = get_object_or_404(ScriptCharacterSuggestion, pk=sug_id, script_version=latest_version)

        try:
            if action == "confirm_suggestion":
                custom_name = request.POST.get("custom_name", "").strip()
                char = confirm_character_suggestion(
                    suggestion=suggestion,
                    actor_membership=actor_membership,
                    custom_name=custom_name,
                )
                messages.success(request, f"Character '{char.name}' confirmed and created!")

            elif action == "merge_suggestion":
                target_char_id = request.POST.get("target_character_id")
                target_char = get_object_or_404(Character, pk=target_char_id, project=project)
                merge_character_alias(
                    suggestion=suggestion,
                    target_character=target_char,
                    actor_membership=actor_membership,
                )
                messages.success(request, f"Suggestion '{suggestion.name}' merged into character '{target_char.name}'!")

            elif action == "reject_suggestion":
                reject_character_suggestion(
                    suggestion=suggestion,
                    actor_membership=actor_membership,
                )
                messages.info(request, f"Suggestion '{suggestion.name}' rejected.")

        except Exception as e:
            messages.error(request, str(e))

        return redirect("script_workspace", slug=project.slug)

    segments = []
    task_links_by_segment = {}
    suggestions = []

    if latest_version:
        segments = list(latest_version.segments.select_related("scene", "character").order_by("segment_number"))
        suggestions = list(latest_version.character_suggestions.all().order_by("-occurrence_count", "name"))

        links = TaskScriptLink.objects.filter(
            script_version=latest_version
        ).select_related("task", "start_segment", "end_segment")

        for link in links:
            for seg_num in range(link.start_segment.segment_number, link.end_segment.segment_number + 1):
                task_links_by_segment.setdefault(seg_num, []).append({
                    "task": link.task,
                    "has_drifted": link.has_text_drifted(),
                })

    characters = list(project.characters.all())
    departments = list(project.departments.all())

    return render(
        request,
        "production/script_workspace.html",
        {
            "project": project,
            "script_doc": doc,
            "latest_version": latest_version,
            "segments": segments,
            "task_links_by_segment": task_links_by_segment,
            "suggestions": suggestions,
            "characters": characters,
            "departments": departments,
        },
    )


@login_required
def create_task_from_segment_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        version_id = request.POST.get("version_id")
        start_seg_id = request.POST.get("start_segment_id")
        end_seg_id = request.POST.get("end_segment_id")
        code = request.POST.get("code", "").strip()
        title = request.POST.get("title", "").strip()
        task_type = request.POST.get("task_type", "video")
        character_id = request.POST.get("character_id")

        script_version = get_object_or_404(ScriptVersion, pk=version_id, script_document__project=project)
        start_segment = get_object_or_404(ScriptSegment, pk=start_seg_id, script_version=script_version)
        end_segment = get_object_or_404(ScriptSegment, pk=end_seg_id, script_version=script_version)

        character = Character.objects.filter(pk=character_id, project=project).first() if character_id else None

        try:
            task = create_task_from_script_selection(
                project=project,
                actor_membership=actor_membership,
                script_version=script_version,
                start_segment=start_segment,
                end_segment=end_segment,
                code=code,
                title=title,
                task_type=task_type,
                character=character,
            )
            messages.success(request, f"Production Task {task.code} created from script selection!")
            return redirect("script_workspace", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return redirect("script_workspace", slug=project.slug)


@login_required
def production_matrix_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    get_object_or_404(Membership, project=project, user=request.user)

    filters = {
        "scene_id": request.GET.get("scene_id"),
        "department_id": request.GET.get("department_id"),
        "task_type": request.GET.get("task_type"),
        "status": request.GET.get("status"),
        "character_id": request.GET.get("character_id"),
    }

    matrix_data = get_production_planning_matrix(project=project, filters=filters)
    characters = project.characters.all()

    return render(
        request,
        "production/production_matrix.html",
        {
            "project": project,
            "characters": characters,
            "filters": filters,
            **matrix_data,
        },
    )
