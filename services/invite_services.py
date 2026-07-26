from datetime import timedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.projects.models import (
    Membership,
    MembershipAgreement,
    ProductionRole,
    Project,
    ProjectInviteToken,
    ProjectTermsVersion,
    RoleAssignment,
)
from services.boundary_services import verify_director_authority, verify_membership_in_project
from services.notification_services import create_notification


@transaction.atomic
def create_project_invite(
    *,
    project: Project,
    actor_membership: Membership,
    default_role: ProductionRole,
    duration_days: int = 7,
    max_uses: int = 1,
) -> ProjectInviteToken:
    verify_director_authority(reviewer=actor_membership, project=project)

    if default_role.project_id != project.id:
        raise ValidationError("Default role must belong to the target project.")

    # DISALLOW PRIVILEGED ROLES ON INVITES
    if (
        default_role.can_accept_final_assets
        or default_role.can_manage_credits
        or default_role.can_assign_tasks
    ):
        raise ValidationError(
            "Invite tokens cannot grant privileged director, producer, or asset acceptance authority."
        )

    expires_at = timezone.now() + timedelta(days=duration_days)

    invite = ProjectInviteToken.objects.create(
        project=project,
        default_role=default_role,
        created_by=actor_membership,
        expires_at=expires_at,
        max_uses=max_uses,
    )

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="project_invite_created",
        object_type="project_invite_token",
        object_id=str(invite.id),
        metadata={"default_role": default_role.name, "token": str(invite.token)},
    )

    return invite


@transaction.atomic
def revoke_project_invite(
    *,
    invite_token: ProjectInviteToken,
    actor_membership: Membership,
) -> ProjectInviteToken:
    verify_director_authority(reviewer=actor_membership, project=invite_token.project)

    invite_token.revoked_at = timezone.now()
    invite_token.save()

    AuditEvent.objects.create(
        project=invite_token.project,
        actor=actor_membership,
        event_type="project_invite_revoked",
        object_type="project_invite_token",
        object_id=str(invite_token.id),
        metadata={"token": str(invite_token.token)},
    )

    return invite_token


@transaction.atomic
def accept_project_invite(
    *,
    token_str: str,
    user,
    credited_name: str = "",
) -> Membership:
    try:
        invite = ProjectInviteToken.objects.select_for_update().get(token=str(token_str))
    except ProjectInviteToken.DoesNotExist:
        raise ValidationError("Invalid or expired invite token.")

    if not invite.is_valid():
        raise ValidationError("This invite token has expired, been revoked, or reached maximum uses.")

    project = invite.project

    # Check existing active membership
    existing_mem = Membership.objects.filter(project=project, user=user).first()
    if existing_mem:
        raise ValidationError(f"User is already a member of project {project.name}.")

    latest_terms = project.terms_versions.order_by("-version_number").first()
    if not latest_terms:
        raise ValidationError("Project does not have an active terms version.")

    name = credited_name or user.display_name or user.username

    membership = Membership.objects.create(
        project=project,
        user=user,
        credited_name=name,
        status=Membership.Status.ACTIVE,
    )

    MembershipAgreement.objects.create(
        membership=membership, terms_version=latest_terms
    )

    RoleAssignment.objects.create(
        membership=membership,
        role=invite.default_role,
        is_department_head=False,
    )

    invite.uses_count += 1
    invite.save()

    create_notification(
        membership=invite.created_by,
        title="Invite Accepted",
        message=f"{name} joined {project.name} as {invite.default_role.name}.",
        link_url=f"/projects/{project.slug}/",
    )

    AuditEvent.objects.create(
        project=project,
        actor=membership,
        event_type="project_invite_accepted",
        object_type="membership",
        object_id=str(membership.id),
        metadata={"token": str(invite.token), "credited_name": name},
    )

    return membership
