from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.credits.models import CreditEntry
from apps.production.models import ProductionTask
from apps.submissions.models import (
    CanonicalSelection,
    DirectorReview,
    Submission,
    SubmissionVersion,
)
from services.boundary_services import verify_director_authority


@transaction.atomic
def accept_submission_version(
    *,
    version: SubmissionVersion,
    reviewer_membership,
    notes: str = "",
    as_alternate: bool = False,
) -> DirectorReview:
    verify_director_authority(
        reviewer=reviewer_membership,
        project=version.submission.task.project,
    )

    locked_version = (
        SubmissionVersion.objects.select_for_update()
        .select_related("submission__task")
        .get(pk=version.pk)
    )

    submission = locked_version.submission
    task = submission.task

    if submission.status == Submission.Status.REJECTED:
        raise ValidationError("A rejected submission cannot be accepted.")

    decision = (
        DirectorReview.Decision.ALTERNATE
        if as_alternate
        else DirectorReview.Decision.ACCEPT
    )

    review = DirectorReview.objects.create(
        version=locked_version,
        reviewer=reviewer_membership,
        decision=decision,
        notes=notes,
    )

    if as_alternate:
        submission.status = Submission.Status.ALTERNATE
        submission.save()
    else:
        submission.status = Submission.Status.ACCEPTED
        submission.save()

        task.status = ProductionTask.Status.SATISFIED
        task.save()

        # Retire existing active CanonicalSelection if any
        active_selection = task.canonical_selections.filter(
            retired_at__isnull=True
        ).first()

        new_selection = CanonicalSelection.objects.create(
            task=task,
            submission_version=locked_version,
            selected_by=reviewer_membership,
            supersedes=active_selection,
            reason=notes or f"Accepted version {locked_version.version_number}",
        )

        if active_selection:
            active_selection.retired_at = timezone.now()
            active_selection.save()

    # Create atomic CreditEntry for accepted work
    CreditEntry.objects.create(
        project=task.project,
        contributor=submission.contributor,
        credited_name=submission.contributor.credited_name,
        role_name="Generation Contributor",
        department_name="Generation Department",
        basis=CreditEntry.Basis.ACCEPTED_WORK,
        status=CreditEntry.Status.ELIGIBLE,
        contribution_summary=f"Generated accepted asset v{locked_version.version_number} for task {task.code}",
        submission_version=locked_version,
    )

    AuditEvent.objects.create(
        project=task.project,
        actor=reviewer_membership,
        event_type="submission_version_accepted",
        object_type="submission_version",
        object_id=str(locked_version.id),
        metadata={
            "task_code": task.code,
            "version_number": locked_version.version_number,
            "as_alternate": as_alternate,
        },
    )

    return review
