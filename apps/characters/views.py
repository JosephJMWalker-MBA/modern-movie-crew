from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.characters.models import Character, CharacterIdentityVersion
from apps.projects.models import Membership, Project, RoleAssignment
from services.character_services import (
    approve_character_identity,
    create_character_identity_version,
)


@login_required
def character_list_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    characters = project.characters.all()
    return render(
        request,
        "characters/character_list.html",
        {"project": project, "characters": characters},
    )


@login_required
def create_character_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        facial_notes = request.POST.get("facial_notes", "")

        character = Character.objects.create(
            project=project, name=name, description=description
        )

        create_character_identity_version(
            character=character,
            version_number=1,
            facial_structure_notes=facial_notes,
            creator_membership=membership,
        )

        messages.success(request, f"Character '{name}' created with Identity v1!")
        return redirect("character_list", slug=project.slug)

    return render(request, "characters/create_character.html", {"project": project})


@login_required
def approve_identity_view(request, slug, identity_id):
    project = get_object_or_404(Project, slug=slug)
    identity_version = get_object_or_404(
        CharacterIdentityVersion, pk=identity_id, character__project=project
    )
    membership = get_object_or_404(Membership, project=project, user=request.user)
    assignment = membership.role_assignments.filter(ends_at__isnull=True).first()

    if not assignment:
        messages.error(request, "You need an active role assignment to approve characters.")
        return redirect("character_list", slug=project.slug)

    try:
        approve_character_identity(
            identity_version=identity_version, reviewer_assignment=assignment
        )
        messages.success(
            request,
            f"Character identity v{identity_version.version_number} approved for {identity_version.character.name}!",
        )
    except Exception as e:
        messages.error(request, str(e))

    return redirect("character_list", slug=project.slug)
