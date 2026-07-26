from django.core.exceptions import ValidationError
from django.db import models


class Submission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In review"
        REVISION_REQUESTED = "revision_requested", "Revision requested"
        ACCEPTED = "accepted", "Accepted"
        ALTERNATE = "alternate", "Accepted as alternate"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    task = models.ForeignKey(
        "production.ProductionTask",
        related_name="submissions",
        on_delete=models.CASCADE,
    )
    contributor = models.ForeignKey(
        "projects.Membership",
        related_name="submissions",
        on_delete=models.PROTECT,
    )
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def latest_version(self):
        return self.versions.order_by("-version_number").first()

    def __str__(self):
        return f"Submission by {self.contributor.credited_name} for {self.task.code} [{self.status}]"


class SubmissionVersion(models.Model):
    submission = models.ForeignKey(
        Submission,
        related_name="versions",
        on_delete=models.CASCADE,
    )
    version_number = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=500)

    external_tool = models.CharField(max_length=100, blank=True)
    prompt_used = models.TextField(blank=True)
    seed = models.CharField(max_length=100, blank=True)
    contributor_notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "projects.Membership",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("submission", "version_number")
        ordering = ("version_number",)

    def save(self, *args, **kwargs):
        if self.pk and self.canonical_uses.exists():
            raise ValidationError(
                "Accepted canonical submission versions are immutable and cannot be updated."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.canonical_uses.exists():
            raise ValidationError(
                "Accepted canonical submission versions are immutable and cannot be deleted."
            )
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.submission.task.code} Submission v{self.version_number}"


class SubmissionAttestation(models.Model):
    version = models.OneToOneField(
        SubmissionVersion,
        related_name="attestation",
        on_delete=models.CASCADE,
    )
    confirmed_authority = models.BooleanField(default=True)
    external_tool = models.CharField(max_length=100)
    commercial_use_allowed = models.BooleanField(default=True)
    likeness_authorized = models.BooleanField(default=True)
    source_asset_disclosure = models.TextField(blank=True)
    attested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attestation for {self.version}"


class DepartmentReview(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        ISSUE_FOUND = "issue_found", "Issue found"
        REVISION_RECOMMENDED = (
            "revision_recommended",
            "Revision recommended",
        )
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    version = models.ForeignKey(
        SubmissionVersion,
        related_name="department_reviews",
        on_delete=models.PROTECT,
    )
    reviewer_assignment = models.ForeignKey(
        "projects.RoleAssignment",
        related_name="department_reviews",
        on_delete=models.PROTECT,
    )
    decision = models.CharField(max_length=30, choices=Decision.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dept Review ({self.reviewer_assignment.role.department.name}): {self.decision}"


class DirectorReview(models.Model):
    class Decision(models.TextChoices):
        ACCEPT = "accept", "Accept"
        ALTERNATE = "alternate", "Accept as alternate"
        REQUEST_REVISION = "revision", "Request revision"
        REJECT = "reject", "Reject"

    version = models.ForeignKey(
        SubmissionVersion,
        related_name="director_reviews",
        on_delete=models.PROTECT,
    )
    reviewer = models.ForeignKey(
        "projects.Membership",
        related_name="director_reviews",
        on_delete=models.PROTECT,
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Director Review: {self.decision} on {self.version}"


class CanonicalSelection(models.Model):
    task = models.ForeignKey(
        "production.ProductionTask",
        related_name="canonical_selections",
        on_delete=models.CASCADE,
    )
    submission_version = models.ForeignKey(
        SubmissionVersion,
        related_name="canonical_uses",
        on_delete=models.PROTECT,
    )
    selected_by = models.ForeignKey(
        "projects.Membership",
        on_delete=models.PROTECT,
    )
    selected_at = models.DateTimeField(auto_now_add=True)
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="superseded_by_set",
        on_delete=models.SET_NULL,
    )
    retired_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-selected_at",)

    def __str__(self):
        status = "Active" if self.retired_at is None else "Retired"
        return f"CanonicalSelection ({status}): {self.task.code} -> v{self.submission_version.version_number}"
