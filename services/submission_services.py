from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.credits.models import CreditEntry
from apps.projects.models import MembershipAgreement, ProjectTermsVersion
from apps.submissions.models import (
    DepartmentReview,
    DirectorReview,
    Submission,
    SubmissionAttestation,
    SubmissionVersion,
)
from services.boundary_services import (
    verify_active_role_assignment,
    verify_department_match,
    verify_director_authority,
    verify_membership_in_project,
)
from services.upload_services import validate_uploaded_file


@transaction.atomic
def create_submission_with_v1(
    *,
    task,
    contributor_membership,
    storage_key: str,
    file_obj=None,
    external_tool: str = "",
    prompt_used: str = "",
    seed: str = "",
    contributor_notes: str = "",
    confirmed_authority: bool = True,
    commercial_use_allowed: bool = True,
    likeness_authorized: bool = True,
    source_asset_disclosure: str = "",
) -> SubmissionVersion:
    verify_membership_in_project(
        membership=contributor_membership, project=task.project
    )

    if file_obj:
        validate_uploaded_file(file_obj)

    if task.status != task.Status.OPEN:
        raise ValidationError(f"Cannot submit to task {task.code} because it is not OPEN.")

    # Check that contributor has accepted current ProjectTermsVersion
    latest_terms = (
        ProjectTermsVersion.objects.filter(project=task.project)
        .order_by("-version_number")
        .first()
    )
    if latest_terms:
        has_accepted = MembershipAgreement.objects.filter(
            membership=contributor_membership, terms_version=latest_terms
        ).exists()
        if not has_accepted:
            raise ValidationError(
                "Contributor must accept the current ProjectTermsVersion before submitting."
            )

    submission = Submission.objects.create(
        task=task,
        contributor=contributor_membership,
        status=Submission.Status.IN_REVIEW,
    )

    version = SubmissionVersion.objects.create(
        submission=submission,
        version_number=1,
        storage_key=storage_key,
        external_tool=external_tool,
        prompt_used=prompt_used,
        seed=seed,
        contributor_notes=contributor_notes,
        created_by=contributor_membership,
    )

    SubmissionAttestation.objects.create(
        version=version,
        confirmed_authority=confirmed_authority,
        external_tool=external_tool,
        commercial_use_allowed=commercial_use_allowed,
        likeness_authorized=likeness_authorized,
        source_asset_disclosure=source_asset_disclosure,
    )

    # Update active task claim if present
    active_claim = task.claims.filter(
        contributor=contributor_membership, status="active"
    ).first()
    if active_claim:
        active_claim.status = "submitted"
        active_claim.save()

    AuditEvent.objects.create(
        project=task.project,
        actor=contributor_membership,
        event_type="submission_v1_created",
        object_type="submission_version",
        object_id=str(version.id),
        metadata={"task_code": task.code, "version_number": 1},
    )

    return version


@transaction.atomic
def submit_department_review(
    *,
    version: SubmissionVersion,
    reviewer_assignment,
    decision: str,
    notes: str = "",
) -> DepartmentReview:
    verify_active_role_assignment(assignment=reviewer_assignment)
    verify_membership_in_project(
        membership=reviewer_assignment.membership,
        project=version.submission.task.project,
    )

    review = DepartmentReview.objects.create(
        version=version,
        reviewer_assignment=reviewer_assignment,
        decision=decision,
        notes=notes,
    )

    CreditEntry.objects.create(
        project=version.submission.task.project,
        contributor=reviewer_assignment.membership,
        credited_name=reviewer_assignment.membership.credited_name,
        role_name=reviewer_assignment.role.name,
        department_name=reviewer_assignment.role.department.name,
        basis=CreditEntry.Basis.RESPONSIBILITY,
        status=CreditEntry.Status.ELIGIBLE,
        contribution_summary=f"Issued department review ({decision}) for task {version.submission.task.code} v{version.version_number}",
        department_review=review,
    )

    AuditEvent.objects.create(
        project=version.submission.task.project,
        actor=reviewer_assignment.membership,
        event_type="department_review_submitted",
        object_type="department_review",
        object_id=str(review.id),
        metadata={
            "task_code": version.submission.task.code,
            "decision": decision,
        },
    )

    return review


@transaction.atomic
def request_submission_revision(
    *,
    version: SubmissionVersion,
    reviewer_membership,
    notes: str = "",
) -> DirectorReview:
    verify_director_authority(
        reviewer=reviewer_membership,
        project=version.submission.task.project,
    )

    submission = version.submission
    task = submission.task

    review = DirectorReview.objects.create(
        version=version,
        reviewer=reviewer_membership,
        decision=DirectorReview.Decision.REQUEST_REVISION,
        notes=notes,
    )

    # Submission status becomes REVISION_REQUESTED
    submission.status = Submission.Status.REVISION_REQUESTED
    submission.save()

    # Note: Task status remains OPEN (it does NOT move globally to revision!)

    AuditEvent.objects.create(
        project=task.project,
        actor=reviewer_membership,
        event_type="submission_revision_requested",
        object_type="director_review",
        object_id=str(review.id),
        metadata={
            "task_code": task.code,
            "version_number": version.version_number,
        },
    )

    return review


@transaction.atomic
def create_submission_v2(
    *,
    submission: Submission,
    contributor_membership,
    storage_key: str,
    file_obj=None,
    external_tool: str = "",
    prompt_used: str = "",
    seed: str = "",
    contributor_notes: str = "",
) -> SubmissionVersion:
    verify_membership_in_project(
        membership=contributor_membership, project=submission.task.project
    )

    if file_obj:
        validate_uploaded_file(file_obj)

    if submission.status != Submission.Status.REVISION_REQUESTED:
        raise ValidationError(
            "Cannot upload revision unless submission is in REVISION_REQUESTED status."
        )

    next_version_num = (submission.latest_version().version_number if submission.latest_version() else 0) + 1

    version = SubmissionVersion.objects.create(
        submission=submission,
        version_number=next_version_num,
        storage_key=storage_key,
        external_tool=external_tool,
        prompt_used=prompt_used,
        seed=seed,
        contributor_notes=contributor_notes,
        created_by=contributor_membership,
    )

    # Return submission status to IN_REVIEW
    submission.status = Submission.Status.IN_REVIEW
    submission.save()

    AuditEvent.objects.create(
        project=submission.task.project,
        actor=contributor_membership,
        event_type="submission_version_created",
        object_type="submission_version",
        object_id=str(version.id),
        metadata={
            "task_code": submission.task.code,
            "version_number": next_version_num,
        },
    )

    return version
