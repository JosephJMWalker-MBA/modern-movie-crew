from datetime import timedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.models import UserFeedback
from apps.projects.models import Project
from services.boundary_services import verify_membership_in_project

ALLOWED_SNAPSHOT_KEYS = {
    "user_agent",
    "page_name",
    "context_type",
    "context_identifier",
    "project_slug",
    "screen_resolution",
}


@transaction.atomic
def submit_user_feedback(
    *,
    user,
    page_url: str,
    page_name: str,
    category: str,
    title: str,
    what_user_was_doing: str,
    ideal_result: str,
    actual_result: str = "",
    severity: str = "medium",
    project: Project = None,
    context_type: str = "",
    context_identifier: str = "",
    user_agent: str = "",
    extra_context: dict = None,
) -> UserFeedback:
    """
    Submits in-app contextual user feedback with strict metadata allowlisting and rate-limiting.
    """
    if not title.strip() or not ideal_result.strip():
        raise ValidationError("Title and Ideal Result ('What would you ideally want to happen here?') are required.")

    # Project boundary validation
    if project:
        membership = project.memberships.filter(user=user).first()
        if not membership and not user.is_staff:
            raise PermissionDenied(f"User {user.username} cannot submit feedback for project {project.slug}.")

    # Rate limiting: max 10 submissions per 5 minutes per user
    recent_count = UserFeedback.objects.filter(
        submitted_by=user,
        created_at__gte=timezone.now() - timedelta(minutes=5),
    ).count()
    if recent_count >= 10:
        raise ValidationError("Feedback submission rate limit exceeded. Please wait a few minutes before submitting again.")

    # Build strict allowlisted snapshot
    snapshot = {}
    if user_agent:
        snapshot["user_agent"] = user_agent[:250]
    if project:
        snapshot["project_slug"] = project.slug
    if context_type:
        snapshot["context_type"] = context_type[:50]
    if context_identifier:
        snapshot["context_identifier"] = str(context_identifier)[:100]

    if extra_context and isinstance(extra_context, dict):
        for k, v in extra_context.items():
            if k in ALLOWED_SNAPSHOT_KEYS:
                snapshot[k] = str(v)[:250]

    feedback = UserFeedback.objects.create(
        submitted_by=user,
        project=project,
        category=category,
        title=title[:200],
        what_user_was_doing=what_user_was_doing,
        actual_result=actual_result,
        ideal_result=ideal_result,
        severity=severity,
        page_url=page_url[:500],
        page_name=page_name[:120],
        context_type=context_type[:50],
        context_identifier=str(context_identifier)[:100],
        context_snapshot=snapshot,
    )

    return feedback


@transaction.atomic
def triage_user_feedback(
    *,
    feedback: UserFeedback,
    actor_user,
    status: str = None,
    internal_notes: str = None,
    duplicate_of: UserFeedback = None,
    github_issue_number: int = None,
    github_issue_url: str = None,
) -> UserFeedback:
    """
    Internal triage service for authorized staff / project admins to triage feedback, add internal notes, group duplicates, or link GitHub issues.
    """
    if feedback.project:
        membership = feedback.project.memberships.filter(user=actor_user).first()
        is_project_admin = membership and membership.role_assignments.filter(
            role__can_accept_final_assets=True,
            ends_at__isnull=True,
        ).exists()
        if not (actor_user.is_staff or is_project_admin):
            raise PermissionDenied("Only authorized staff or project leads can triage feedback.")
    elif not actor_user.is_staff:
        raise PermissionDenied("Only staff users can triage global feedback.")

    if status:
        feedback.status = status
    if internal_notes is not None:
        feedback.internal_notes = internal_notes
    if duplicate_of:
        if duplicate_of.id == feedback.id:
            raise ValidationError("Feedback item cannot be marked as a duplicate of itself.")
        feedback.duplicate_of = duplicate_of
        feedback.status = UserFeedback.Status.DUPLICATE
    if github_issue_number is not None:
        feedback.github_issue_number = github_issue_number
    if github_issue_url is not None:
        feedback.github_issue_url = github_issue_url

    feedback.save()
    return feedback
