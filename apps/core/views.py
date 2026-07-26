from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.models import AuditEvent, Notification
from apps.projects.models import Membership, Project


def dashboard_view(request):
    projects = Project.objects.all()
    return render(request, "dashboard.html", {"projects": projects})


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.display_name = user.username
            user.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def notifications_view(request):
    memberships = Membership.objects.filter(user=request.user)
    notifications_qs = Notification.objects.filter(membership__in=memberships)

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
    memberships = Membership.objects.filter(user=request.user)
    notif = get_object_or_404(Notification, pk=notif_id, membership__in=memberships)
    notif.is_read = True
    notif.save()
    return redirect("notifications")


@login_required
def activity_feed_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    audit_events = project.audit_events.select_related("actor").order_by("-created_at")

    paginator = Paginator(audit_events, 20)
    page_number = request.GET.get("page", 1)
    events_page = paginator.get_page(page_number)

    return render(
        request,
        "core/activity_feed.html",
        {"project": project, "events_page": events_page},
    )
