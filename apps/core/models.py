from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditEvent(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        related_name="audit_events",
        on_delete=models.CASCADE,
        db_index=True,
    )
    actor = models.ForeignKey(
        "projects.Membership",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    event_type = models.CharField(max_length=100, db_index=True)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["project", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Audit events are append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Audit events are append-only and cannot be deleted.")

    def __str__(self):
        return f"[{self.created_at}] {self.event_type} on {self.object_type}:{self.object_id}"


class Notification(models.Model):
    membership = models.ForeignKey(
        "projects.Membership",
        related_name="notifications",
        on_delete=models.CASCADE,
        db_index=True,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link_url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["membership", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"Notification for {self.membership.credited_name}: {self.title}"


# IN-APP CONTEXTUAL USER FEEDBACK ENTITY (Issue #8)

class UserFeedback(TimeStampedModel):
    class Category(models.TextChoices):
        BUG = "bug", "Bug"
        MISSING_CAPABILITY = "missing_capability", "Missing capability"
        WORKFLOW_IMPROVEMENT = "workflow_improvement", "Workflow improvement"
        CONFUSING_INTERFACE = "confusing_interface", "Confusing interface"
        PERFORMANCE = "performance", "Performance problem"
        ACCESSIBILITY = "accessibility", "Accessibility issue"
        FEATURE_REQUEST = "feature_request", "Feature request"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        LOW = "low", "Low / Minor"
        MEDIUM = "medium", "Medium / Normal"
        HIGH = "high", "High / Important"
        CRITICAL = "critical", "Critical / Blocker"

    class Status(models.TextChoices):
        NEW = "new", "New"
        TRIAGED = "triaged", "Triaged"
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        DECLINED = "declined", "Declined"
        DUPLICATE = "duplicate", "Duplicate"

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="submitted_feedback",
        on_delete=models.CASCADE,
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        related_name="feedback_entries",
        on_delete=models.CASCADE,
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.WORKFLOW_IMPROVEMENT,
    )
    title = models.CharField(max_length=200)
    what_user_was_doing = models.TextField()
    actual_result = models.TextField(blank=True)
    ideal_result = models.TextField()  # "What would you ideally want to happen here?"
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )

    page_url = models.CharField(max_length=500)
    page_name = models.CharField(max_length=120)
    context_type = models.CharField(max_length=50, blank=True)
    context_identifier = models.CharField(max_length=100, blank=True)
    context_snapshot = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    duplicate_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="duplicates",
        on_delete=models.SET_NULL,
    )
    github_issue_number = models.IntegerField(null=True, blank=True)
    github_issue_url = models.URLField(blank=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Feedback #{self.id}: {self.title} [{self.get_status_display()}]"
