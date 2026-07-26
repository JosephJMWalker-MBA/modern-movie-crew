from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        DEVELOPMENT = "development", "Development"
        PRODUCTION = "production", "Production"
        POST = "post", "Post-production"
        COMPLETE = "complete", "Complete"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    synopsis = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DEVELOPMENT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProjectTermsVersion(models.Model):
    project = models.ForeignKey(
        Project,
        related_name="terms_versions",
        on_delete=models.CASCADE,
    )
    version_number = models.PositiveIntegerField()
    terms_text = models.TextField()
    license_policy = models.TextField(blank=True)
    credit_policy = models.TextField(blank=True)
    effective_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "version_number")
        ordering = ("-version_number",)

    def __str__(self):
        return f"{self.project.name} Terms v{self.version_number}"


class Department(models.Model):
    project = models.ForeignKey(
        Project,
        related_name="departments",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("project", "name")
        ordering = ("sort_order", "name")

    def __str__(self):
        return f"{self.name} ({self.project.name})"


class Membership(models.Model):
    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    project = models.ForeignKey(
        Project,
        related_name="memberships",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="project_memberships",
        on_delete=models.CASCADE,
    )
    credited_name = models.CharField(max_length=160)
    public_handle = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INVITED,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")

    def __str__(self):
        return f"{self.credited_name} on {self.project.name}"


class MembershipAgreement(models.Model):
    membership = models.ForeignKey(
        Membership,
        related_name="agreements",
        on_delete=models.CASCADE,
    )
    terms_version = models.ForeignKey(
        ProjectTermsVersion,
        related_name="accepted_agreements",
        on_delete=models.PROTECT,
    )
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("membership", "terms_version")

    def clean(self):
        if (
            self.membership_id
            and self.terms_version_id
            and self.membership.project_id != self.terms_version.project_id
        ):
            raise ValidationError(
                "Membership and ProjectTermsVersion must belong to the same project."
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.membership} accepted v{self.terms_version.version_number}"


class ProductionRole(models.Model):
    project = models.ForeignKey(
        Project,
        related_name="roles",
        on_delete=models.CASCADE,
    )
    department = models.ForeignKey(
        Department,
        related_name="roles",
        on_delete=models.PROTECT,
    )
    name = models.CharField(max_length=120)

    can_assign_tasks = models.BooleanField(default=False)
    can_approve_department_work = models.BooleanField(default=False)
    can_accept_final_assets = models.BooleanField(default=False)
    can_manage_credits = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "department", "name")

    def clean(self):
        if (
            self.project_id
            and self.department_id
            and self.department.project_id != self.project_id
        ):
            raise ValidationError(
                "Department must belong to the same project as ProductionRole."
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.department.name}"


class RoleAssignment(models.Model):
    membership = models.ForeignKey(
        Membership,
        related_name="role_assignments",
        on_delete=models.CASCADE,
    )
    role = models.ForeignKey(
        ProductionRole,
        related_name="assignments",
        on_delete=models.PROTECT,
    )
    starts_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_department_head = models.BooleanField(default=False)

    def clean(self):
        if (
            self.membership_id
            and self.role_id
            and self.membership.project_id != self.role.project_id
        ):
            raise ValidationError(
                "Membership and ProductionRole must belong to the same project."
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def is_active(self):
        return self.ends_at is None

    def __str__(self):
        return f"{self.membership.credited_name} as {self.role.name}"
