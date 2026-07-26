from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.credits.models import CreditEntry
from apps.projects.models import Membership, Project


@login_required
def credit_ledger_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    credits_list = (
        CreditEntry.objects.filter(project=project)
        .select_related("contributor", "submission_version")
        .order_by("department_name", "role_name", "credited_name", "id")
    )
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
