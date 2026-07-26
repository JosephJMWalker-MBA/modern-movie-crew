from datetime import timedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.credits.models import CreditEntry
from apps.production.models import (
    PacketSection,
    ProductionTask,
    TaskClaim,
)
from services.boundary_services import (
    verify_active_role_assignment,
    verify_department_match,
    verify_membership_in_project,
)


@transaction.atomic
def approve_packet_section(
    *,
    packet_section: PacketSection,
    reviewer_assignment,
) -> PacketSection:
    verify_active_role_assignment(assignment=reviewer_assignment)
    verify_membership_in_project(
        membership=reviewer_assignment.membership,
        project=packet_section.task.project,
    )
    verify_department_match(
        assignment=reviewer_assignment,
        target_department=packet_section.department,
    )

    if not reviewer_assignment.role.can_approve_department_work:
        raise PermissionDenied(
            "Role assignment cannot approve department packet work."
        )

    packet_section.status = PacketSection.Status.APPROVED
    packet_section.approved_by = reviewer_assignment.membership
    packet_section.approved_at = timezone.now()
    packet_section.save()

    CreditEntry.objects.create(
        project=packet_section.task.project,
        contributor=reviewer_assignment.membership,
        credited_name=reviewer_assignment.membership.credited_name,
        role_name=reviewer_assignment.role.name,
        department_name=reviewer_assignment.role.department.name,
        basis=CreditEntry.Basis.RESPONSIBILITY,
        status=CreditEntry.Status.ELIGIBLE,
        contribution_summary=f"Approved packet section '{packet_section.section_type}' for task {packet_section.task.code}",
        packet_section=packet_section,
    )

    AuditEvent.objects.create(
        project=packet_section.task.project,
        actor=reviewer_assignment.membership,
        event_type="packet_section_approved",
        object_type="packet_section",
        object_id=str(packet_section.id),
        metadata={
            "task_code": packet_section.task.code,
            "section_type": packet_section.section_type,
        },
    )

    return packet_section


@transaction.atomic
def transition_task_to_open(
    *,
    task: ProductionTask,
    actor_membership,
) -> ProductionTask:
    verify_membership_in_project(
        membership=actor_membership, project=task.project
    )

    # Check unapproved required packet sections
    unapproved_sections = task.packet_sections.filter(required=True).exclude(
        status=PacketSection.Status.APPROVED
    )
    if unapproved_sections.exists():
        raise ValidationError(
            "Cannot open task until all required packet sections are approved."
        )

    # Check character links
    for link in task.character_links.all():
        if link.character_identity_version.status != "approved":
            raise ValidationError(
                f"Cannot open task until character identity for {link.character.name} is approved."
            )

    task.status = ProductionTask.Status.OPEN
    task.save()

    AuditEvent.objects.create(
        project=task.project,
        actor=actor_membership,
        event_type="task_opened",
        object_type="production_task",
        object_id=str(task.id),
        metadata={"task_code": task.code},
    )

    return task


@transaction.atomic
def claim_production_task(
    *,
    task: ProductionTask,
    contributor_membership,
    duration_hours: int = 24,
) -> TaskClaim:
    verify_membership_in_project(
        membership=contributor_membership, project=task.project
    )

    if task.status != ProductionTask.Status.OPEN:
        raise ValidationError(
            f"Task {task.code} is not currently open for claims."
        )

    if task.claim_mode == ProductionTask.ClaimMode.SINGLE:
        active_claims = task.claims.filter(status=TaskClaim.Status.ACTIVE)
        if active_claims.exists():
            raise ValidationError(
                f"Task {task.code} already has an active claim."
            )

    expires_at = timezone.now() + timedelta(hours=duration_hours)

    claim = TaskClaim.objects.create(
        task=task,
        contributor=contributor_membership,
        expires_at=expires_at,
        status=TaskClaim.Status.ACTIVE,
    )

    AuditEvent.objects.create(
        project=task.project,
        actor=contributor_membership,
        event_type="task_claimed",
        object_type="task_claim",
        object_id=str(claim.id),
        metadata={
            "task_code": task.code,
            "expires_at": expires_at.isoformat(),
        },
    )

    return claim
