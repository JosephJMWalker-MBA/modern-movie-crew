from django.core.exceptions import ValidationError
from django.db import models


class CreditEntry(models.Model):
    class Basis(models.TextChoices):
        ROLE = "role", "Role assignment"
        RESPONSIBILITY = "responsibility", "Departmental responsibility"
        ACCEPTED_WORK = "accepted_work", "Accepted work contribution"
        DIRECTOR = "director", "Direction and creative authority"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ELIGIBLE = "eligible", "Eligible"
        VERIFIED = "verified", "Verified"
        RESCINDED = "rescinded", "Rescinded"

    project = models.ForeignKey(
        "projects.Project",
        related_name="credit_entries",
        on_delete=models.CASCADE,
        db_index=True,
    )
    contributor = models.ForeignKey(
        "projects.Membership",
        related_name="credit_entries",
        on_delete=models.PROTECT,
    )
    credited_name = models.CharField(max_length=160)
    role_name = models.CharField(max_length=120)
    department_name = models.CharField(max_length=120)
    basis = models.CharField(max_length=30, choices=Basis.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ELIGIBLE,
        db_index=True,
    )
    is_final_cut = models.BooleanField(default=False, db_index=True)
    contribution_summary = models.TextField(blank=True)

    submission_version = models.ForeignKey(
        "submissions.SubmissionVersion",
        null=True,
        blank=True,
        related_name="credit_entries",
        on_delete=models.PROTECT,
    )
    character_identity_version = models.ForeignKey(
        "characters.CharacterIdentityVersion",
        null=True,
        blank=True,
        related_name="credit_entries",
        on_delete=models.PROTECT,
    )
    character_look = models.ForeignKey(
        "characters.CharacterLook",
        null=True,
        blank=True,
        related_name="credit_entries",
        on_delete=models.PROTECT,
    )
    packet_section = models.ForeignKey(
        "production.PacketSection",
        null=True,
        blank=True,
        related_name="credit_entries",
        on_delete=models.PROTECT,
    )
    department_review = models.ForeignKey(
        "submissions.DepartmentReview",
        null=True,
        blank=True,
        related_name="credit_entries",
        on_delete=models.PROTECT,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def clean(self):
        if self.pk:
            orig = CreditEntry.objects.get(pk=self.pk)
            if (
                orig.credited_name != self.credited_name
                or orig.role_name != self.role_name
                or orig.department_name != self.department_name
            ):
                raise ValidationError(
                    "CreditEntry snapshot fields (credited_name, role_name, department_name) are immutable once created."
                )

        if (
            self.project_id
            and self.contributor_id
            and self.project_id != self.contributor.project_id
        ):
            raise ValidationError(
                "Contributor must belong to the credit entry's project."
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Credit: {self.credited_name} ({self.role_name}) - {self.basis}"


class ProjectProvenanceSnapshot(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        related_name="provenance_snapshots",
        on_delete=models.CASCADE,
        db_index=True,
    )
    version_number = models.PositiveIntegerField()
    published_at = models.DateTimeField(auto_now_add=True, db_index=True)
    published_by = models.ForeignKey(
        "projects.Membership",
        related_name="published_snapshots",
        on_delete=models.PROTECT,
    )
    snapshot_title = models.CharField(max_length=200, blank=True)
    manifest_data = models.JSONField(default=dict)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("project", "version_number")
        ordering = ("-version_number",)

    def clean(self):
        if self.pk:
            raise ValidationError(
                "ProjectProvenanceSnapshot records are immutable and cannot be updated once published."
            )

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                "ProjectProvenanceSnapshot records are immutable and cannot be updated once published."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("ProjectProvenanceSnapshot records are immutable and cannot be deleted.")

    def __str__(self):
        return f"{self.project.name} Provenance Snapshot v{self.version_number}"
