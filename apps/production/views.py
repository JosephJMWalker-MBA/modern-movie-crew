from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.characters.models import Character, CharacterIdentityVersion
from apps.production.models import (
    Act,
    CharacterTaskLink,
    PacketSection,
    ProductionTask,
    Scene,
    Sequence,
)
from apps.projects.models import Department, Membership, Project
from services.production_services import (
    approve_packet_section,
    claim_production_task,
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
    if request.method == "POST":
        code = request.POST.get("code")
        title = request.POST.get("title")
        task_type = request.POST.get("task_type", "video")
        character_id = request.POST.get("character_id")

        # Ensure Act 1 -> Sequence 1 -> Scene 1 exists
        act, _ = Act.objects.get_or_create(project=project, act_number=1, defaults={"title": "Act I"})
        seq, _ = Sequence.objects.get_or_create(act=act, sequence_number=1, defaults={"title": "Sequence A"})
        scene, _ = Scene.objects.get_or_create(sequence=seq, scene_number=1, defaults={"title": "Scene 1"})

        task = ProductionTask.objects.create(
            project=project, scene=scene, code=code, title=title, task_type=task_type
        )

        # Create story packet section
        art_dept = project.departments.filter(name="Art Department").first() or project.departments.first()
        PacketSection.objects.create(
            task=task,
            department=art_dept,
            section_type=PacketSection.SectionType.STORY,
            content=f"Story prompt for {title}",
            required=True,
        )

        # Link character if selected
        if character_id:
            character = get_object_or_404(Character, pk=character_id, project=project)
            approved_id = character.identity_versions.filter(status="approved").first()
            if approved_id:
                CharacterTaskLink.objects.create(
                    task=task, character=character, character_identity_version=approved_id
                )

        messages.success(request, f"Task '{code}' created!")
        return redirect("task_detail", slug=project.slug, task_id=task.id)

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
