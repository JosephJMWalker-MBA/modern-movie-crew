from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.characters.models import Character
from apps.production.models import PacketSection, ProductionTask
from apps.projects.models import Membership, Project
from services.production_services import (
    approve_packet_section,
    claim_production_task,
    create_production_task_with_packet,
    transition_task_to_open,
)


@login_required
def project_board_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    acts = project.acts.prefetch_related("sequences__scenes__tasks__packet_sections").all()
    user_membership = Membership.objects.filter(project=project, user=request.user).first()
    return render(
        request,
        "production/board.html",
        {"project": project, "acts": acts, "user_membership": user_membership},
    )


@login_required
def create_task_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        code = request.POST.get("code")
        title = request.POST.get("title")
        task_type = request.POST.get("task_type", "video")
        character_id = request.POST.get("character_id")

        character = None
        if character_id:
            character = get_object_or_404(Character, pk=character_id, project=project)

        try:
            task = create_production_task_with_packet(
                project=project,
                actor_membership=membership,
                code=code,
                title=title,
                task_type=task_type,
                character=character,
            )
            messages.success(request, f"Task '{code}' created!")
            return redirect("task_detail", slug=project.slug, task_id=task.id)
        except Exception as e:
            messages.error(request, str(e))

    characters = project.characters.all()
    return render(request, "production/create_task.html", {"project": project, "characters": characters})


@login_required
def task_detail_view(request, slug, task_id):
    project = get_object_or_404(Project, slug=slug)
    task = get_object_or_404(ProductionTask, pk=task_id, project=project)
    membership = Membership.objects.filter(project=project, user=request.user).first()
    sections = task.packet_sections.all()
    submissions = task.submissions.prefetch_related("versions__attestation", "versions__director_reviews", "versions__department_reviews").all()
    active_canonical = task.active_canonical_selection()

    return render(
        request,
        "production/task_detail.html",
        {
            "project": project,
            "task": task,
            "membership": membership,
            "sections": sections,
            "submissions": submissions,
            "active_canonical": active_canonical,
        },
    )


@login_required
def approve_section_view(request, slug, section_id):
    project = get_object_or_404(Project, slug=slug)
    section = get_object_or_404(PacketSection, pk=section_id, task__project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)
    assignment = membership.role_assignments.filter(ends_at__isnull=True).first()

    if not assignment:
        messages.error(request, "Active role assignment required to approve packet sections.")
        return redirect("task_detail", slug=project.slug, task_id=section.task.id)

    try:
        approve_packet_section(packet_section=section, reviewer_assignment=assignment)
        messages.success(request, f"Packet section '{section.section_type}' approved!")
    except Exception as e:
        messages.error(request, str(e))

    return redirect("task_detail", slug=project.slug, task_id=section.task.id)


@login_required
def open_task_view(request, slug, task_id):
    project = get_object_or_404(Project, slug=slug)
    task = get_object_or_404(ProductionTask, pk=task_id, project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    try:
        transition_task_to_open(task=task, actor_membership=membership)
        messages.success(request, f"Task {task.code} is now OPEN for contributor claims!")
    except Exception as e:
        messages.error(request, str(e))

    return redirect("task_detail", slug=project.slug, task_id=task.id)


@login_required
def claim_task_view(request, slug, task_id):
    project = get_object_or_404(Project, slug=slug)
    task = get_object_or_404(ProductionTask, pk=task_id, project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    try:
        claim_production_task(task=task, contributor_membership=membership)
        messages.success(request, f"Task {task.code} claimed successfully!")
    except Exception as e:
        messages.error(request, str(e))

    return redirect("task_detail", slug=project.slug, task_id=task.id)
