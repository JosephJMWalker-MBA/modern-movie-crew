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
