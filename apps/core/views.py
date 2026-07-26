from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.forms import CustomUserCreationForm
from apps.core.models import AuditEvent, Notification
from apps.projects.models import Membership, Project

SENSITIVE_METADATA_KEYS = {"token", "storage_key", "password", "secret", "seed"}


def health_check_view(request):
    try:
        connection.ensure_connection()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        return JsonResponse({"status": "unhealthy", "database": db_status}, status=503)

    return JsonResponse({"status": "healthy", "database": db_status})


def custom_404_view(request, exception=None):
    return render(request, "404.html", status=404)


def custom_500_view(request):
    return render(request, "500.html", status=500)


def dashboard_view(request):
    projects = Project.objects.all().order_by("-created_at", "id")
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

            # Prevent open redirects
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
        notif = get_object_or_404(Notification, pk=notif_id, membership__user=request.user)
        notif.is_read = True
        notif.save()
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

    sanitized_events = []
    for event in events_page:
        clean_meta = {
            k: v for k, v in (event.metadata or {}).items()
            if k.lower() not in SENSITIVE_METADATA_KEYS
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
