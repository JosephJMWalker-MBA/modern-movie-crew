from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.projects.models import Project


@login_required
def credit_ledger_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    credits_list = project.credits.select_related("contributor", "role_assignment", "submission_version").all()
    audit_events = project.audit_events.select_related("actor").order_by("-created_at")[:20]

    return render(
        request,
        "credits/ledger.html",
        {
            "project": project,
            "credits_list": credits_list,
            "audit_events": audit_events,
        },
    )
