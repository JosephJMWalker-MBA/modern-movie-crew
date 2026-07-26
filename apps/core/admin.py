from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "project",
        "actor",
        "event_type",
        "object_type",
        "object_id",
    )
    list_filter = ("event_type", "object_type", "project")
    readonly_fields = (
        "project",
        "actor",
        "event_type",
        "object_type",
        "object_id",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
