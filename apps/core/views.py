import logging
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection, models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.forms import CustomUserCreationForm
from apps.core.models import AuditEvent, Notification
from apps.projects.models import Membership, Project

logger = logging.getLogger("django")

ALLOWED_ACTIVITY_FIELDS_BY_EVENT = {
    "project_created": {"project_name"},
    "crew_member_added": {"credited_name", "role_name"},
    "character_created": {"character_name"},
    "character_identity_approved": {"character_name", "version_number"},
    "character_look_approved": {"character_name", "look_name"},
    "production_task_created": {"task_code"},
    "packet_section_approved": {"task_code", "section_type"},
    "task_opened": {"task_code"},
    "task_claimed": {"task_code"},
    "submission_v1_created": {"task_code", "version_number"},
    "department_review_submitted": {"task_code", "decision"},
    "submission_revision_requested": {"task_code", "version_number"},
    "submission_version_created": {"task_code", "version_number"},
    "submission_version_accepted": {"task_code", "version_number", "as_alternate"},
    "project_invite_created": {"default_role"},
    "project_invite_revoked": {},
    "project_invite_accepted": {"credited_name"},
    "provenance_snapshot_published": {"version_number"},
}


def health_check_view(request):
    try:
        connection.ensure_connection()
        db_status = "connected"
        status_code = 200
        client_msg = "healthy"
        db_client_msg = "connected"
    except Exception as e:
        logger.error("Database connection failure in health check", exc_info=True)
        status_code = 503
        client_msg = "unhealthy"
        db_client_msg = "unavailable"

    return JsonResponse({"status": client_msg, "database": db_client_msg}, status=status_code)


def custom_404_view(request, exception=None):
    return render(request, "404.html", status=404)


def custom_500_view(request):
    return render(request, "500.html", status=500)


@login_required
def dashboard_view(request):
    # Dashboard Privacy: Filter projects where user is an active member or project is public
    user_project_ids = Membership.objects.filter(user=request.user).values_list("project_id", flat=True)
    projects = Project.objects.filter(
        models.Q(id__in=user_project_ids) | models.Q(is_public=True)
    ).distinct().order_by("-created_at", "id")

    return render(request, "dashboard.html", {"projects": projects})


def register_view(request):
    next_url = request.GET.get("next", "")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.display_name = user.username
            user.save()
            login(request, user)

            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def notifications_view(request):
    notifications_qs = (
        Notification.objects.filter(membership__user=request.user)
        .select_related("membership__project")
        .order_by("-created_at", "-id")
    )

    paginator = Paginator(notifications_qs, 15)
    page_number = request.GET.get("page", 1)
    notifications_page = paginator.get_page(page_number)

    return render(
        request,
        "core/notifications.html",
        {"notifications_page": notifications_page},
    )


@login_required
def mark_notification_read_view(request, notif_id):
    if request.method == "POST":
        from services.notification_services import mark_notification_as_read
        try:
            mark_notification_as_read(notif_id=notif_id, user=request.user)
        except Exception as e:
            messages.error(request, str(e))
    return redirect("notifications")


@login_required
def activity_feed_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    user_membership = get_object_or_404(Membership, project=project, user=request.user)

    audit_events_qs = (
        project.audit_events.select_related("actor")
        .order_by("-created_at", "-id")
    )

    paginator = Paginator(audit_events_qs, 20)
    page_number = request.GET.get("page", 1)
    events_page = paginator.get_page(page_number)

    # POSITIVE ALLOWLIST PER EVENT TYPE FOR ACTIVITY FEED METADATA
    sanitized_events = []
    for event in events_page:
        allowed_keys = ALLOWED_ACTIVITY_FIELDS_BY_EVENT.get(event.event_type, set())
        clean_meta = {
            k: v for k, v in (event.metadata or {}).items()
            if k in allowed_keys
        }
        sanitized_events.append({
            "event_type": event.event_type,
            "actor": event.actor,
            "object_type": event.object_type,
            "object_id": event.object_id,
            "created_at": event.created_at,
            "metadata": clean_meta,
        })

    return render(
        request,
        "core/activity_feed.html",
        {
            "project": project,
            "events_page": events_page,
            "sanitized_events": sanitized_events,
        },
    )
