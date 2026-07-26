from django.core.exceptions import ValidationError
from django.db import models


class CreditEntry(models.Model):
    class Basis(models.TextChoices):
        ROLE = "role", "Production role"
        RESOURCE = "resource", "Approved resource"
        RESPONSIBILITY = (
            "responsibility",
            "Creative responsibility / stewardship",
        )
        ACCEPTED_WORK = "accepted_work", "Accepted contribution"
        FINAL_CUT = "final_cut", "Used in final cut"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ELIGIBLE = "eligible", "Eligible"
        CONFIRMED = "confirmed", "Confirmed"
        WITHHELD = "withheld", "Withheld"

    project = models.ForeignKey(
        "projects.Project",
        related_name="credits",
        on_delete=models.CASCADE,
    )
    contributor = models.ForeignKey(
        "projects.Membership",
        related_name="credit_entries",
        on_delete=models.PROTECT,
    )

    # Historical snapshot fields
    credited_name = models.CharField(max_length=160)
    role_name = models.CharField(max_length=120)
    department_name = models.CharField(max_length=120)

    basis = models.CharField(max_length=30, choices=Basis.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    contribution_summary = models.TextField(blank=True)

    # Source object links
    role_assignment = models.ForeignKey(
        "projects.RoleAssignment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    packet_section = models.ForeignKey(
        "production.PacketSection",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    resource = models.ForeignKey(
        "production.Resource",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    character_identity_version = models.ForeignKey(
        "characters.CharacterIdentityVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    character_look = models.ForeignKey(
        "characters.CharacterLook",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    voice_profile = models.ForeignKey(
        "characters.VoiceProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    performance_profile = models.ForeignKey(
        "characters.PerformanceProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    department_review = models.ForeignKey(
        "submissions.DepartmentReview",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    submission_version = models.ForeignKey(
        "submissions.SubmissionVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    appears_in_screen_credits = models.BooleanField(default=True)
    final_order = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.contributor_id and self.project_id:
            if self.contributor.project_id != self.project_id:
                raise ValidationError(
                    "Contributor membership must belong to the CreditEntry project."
                )

        if self.pk:
            # Immutability check for snapshot fields
            original = CreditEntry.objects.get(pk=self.pk)
            if (
                original.credited_name != self.credited_name
                or original.role_name != self.role_name
                or original.department_name != self.department_name
            ):
                raise ValidationError(
                    "Historical credit snapshot names (credited_name, role_name, department_name) cannot be altered once recorded."
                )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Credit ({self.basis}): {self.credited_name} as {self.role_name} [{self.status}]"
