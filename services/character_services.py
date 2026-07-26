from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.characters.models import (
    Character,
    CharacterIdentityVersion,
    CharacterLook,
    CharacterSceneState,
)
from apps.core.models import AuditEvent
from apps.credits.models import CreditEntry
from services.boundary_services import (
    verify_active_role_assignment,
    verify_department_match,
    verify_membership_in_project,
)


@transaction.atomic
def create_character_with_identity(
    *,
    project,
    creator_membership,
    name: str,
    description: str = "",
    facial_notes: str = "",
) -> Character:
    verify_membership_in_project(membership=creator_membership, project=project)

    character = Character.objects.create(
        project=project, name=name, description=description
    )

    identity_v1 = CharacterIdentityVersion.objects.create(
        character=character,
        version_number=1,
        facial_structure_notes=facial_notes,
        status=CharacterIdentityVersion.Status.DRAFT,
    )

    AuditEvent.objects.create(
        project=project,
        actor=creator_membership,
        event_type="character_created",
        object_type="character",
        object_id=str(character.id),
        metadata={"character_name": name},
    )

    return character


@transaction.atomic
def create_character_identity_version(
    *,
    character: Character,
    version_number: int,
    facial_structure_notes: str = "",
    body_type: str = "",
    canonical_reference_image: str = "",
    creator_membership,
) -> CharacterIdentityVersion:
    verify_membership_in_project(
        membership=creator_membership, project=character.project
    )

    identity_version = CharacterIdentityVersion.objects.create(
        character=character,
        version_number=version_number,
        facial_structure_notes=facial_structure_notes,
        body_type=body_type,
        canonical_reference_image=canonical_reference_image,
        status=CharacterIdentityVersion.Status.DRAFT,
    )

    AuditEvent.objects.create(
        project=character.project,
        actor=creator_membership,
        event_type="character_identity_version_created",
        object_type="character_identity_version",
        object_id=str(identity_version.id),
        metadata={
            "character_name": character.name,
            "version_number": version_number,
        },
    )

    return identity_version


@transaction.atomic
def approve_character_identity(
    *,
    identity_version: CharacterIdentityVersion,
    reviewer_assignment,
) -> CharacterIdentityVersion:
    verify_active_role_assignment(assignment=reviewer_assignment)
    verify_membership_in_project(
        membership=reviewer_assignment.membership,
        project=identity_version.character.project,
    )

    if not reviewer_assignment.role.can_approve_department_work:
        raise PermissionDenied("Role cannot approve character identity work.")

    identity_version.status = CharacterIdentityVersion.Status.APPROVED
    identity_version.approved_by = reviewer_assignment.membership
    identity_version.approved_at = timezone.now()
    identity_version.save()

    # Supersede older identity versions if any
    CharacterIdentityVersion.objects.filter(
        character=identity_version.character,
        status=CharacterIdentityVersion.Status.APPROVED,
    ).exclude(pk=identity_version.pk).update(
        status=CharacterIdentityVersion.Status.SUPERSEDED
    )

    # Record Credit
    CreditEntry.objects.create(
        project=identity_version.character.project,
        contributor=reviewer_assignment.membership,
        credited_name=reviewer_assignment.membership.credited_name,
        role_name=reviewer_assignment.role.name,
        department_name=reviewer_assignment.role.department.name,
        basis=CreditEntry.Basis.RESPONSIBILITY,
        status=CreditEntry.Status.ELIGIBLE,
        contribution_summary=f"Approved Character Identity v{identity_version.version_number} for {identity_version.character.name}",
        character_identity_version=identity_version,
    )

    AuditEvent.objects.create(
        project=identity_version.character.project,
        actor=reviewer_assignment.membership,
        event_type="character_identity_approved",
        object_type="character_identity_version",
        object_id=str(identity_version.id),
        metadata={
            "character_name": identity_version.character.name,
            "version_number": identity_version.version_number,
        },
    )

    return identity_version


@transaction.atomic
def create_and_approve_character_look(
    *,
    character: Character,
    name: str,
    wardrobe_description: str = "",
    creator_assignment,
) -> CharacterLook:
    verify_active_role_assignment(assignment=creator_assignment)
    verify_membership_in_project(
        membership=creator_assignment.membership, project=character.project
    )

    look = CharacterLook.objects.create(
        character=character,
        name=name,
        wardrobe_description=wardrobe_description,
        status=CharacterLook.Status.APPROVED,
        created_by=creator_assignment.membership,
    )

    CreditEntry.objects.create(
        project=character.project,
        contributor=creator_assignment.membership,
        credited_name=creator_assignment.membership.credited_name,
        role_name=creator_assignment.role.name,
        department_name=creator_assignment.role.department.name,
        basis=CreditEntry.Basis.RESPONSIBILITY,
        status=CreditEntry.Status.ELIGIBLE,
        contribution_summary=f"Designed costume look '{name}' for {character.name}",
        character_look=look,
    )

    AuditEvent.objects.create(
        project=character.project,
        actor=creator_assignment.membership,
        event_type="character_look_approved",
        object_type="character_look",
        object_id=str(look.id),
        metadata={"character_name": character.name, "look_name": name},
    )

    return look
