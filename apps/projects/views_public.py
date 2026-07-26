from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.models import Membership, Project
from services.publication_services import (
    export_credits_csv,
    export_credits_json,
    get_latest_published_snapshot,
    publish_project_provenance_snapshot,
)


def public_project_view(request, slug):
    project = get_object_or_404(Project, slug=slug)

    # Privacy check: If project is private, check user membership
    if not project.is_public:
        if not request.user.is_authenticated:
            raise Http404("Project is private.")
        user_mem = Membership.objects.filter(project=project, user=request.user).first()
        if not user_mem:
            raise Http404("Project is private.")

    snapshot = get_latest_published_snapshot(project)
    manifest = snapshot.manifest_data if snapshot else None

    # Group credits by department if manifest exists
    grouped_credits = {}
    if manifest:
        for c in manifest.get("credits", []):
            dept = c.get("department_name", "General")
            if dept not in grouped_credits:
                grouped_credits[dept] = []
            grouped_credits[dept].append(c)

    return render(
        request,
        "public/public_project.html",
        {
            "project": project,
            "snapshot": snapshot,
            "manifest": manifest,
            "grouped_credits": grouped_credits,
        },
    )


def public_credit_roll_view(request, slug):
    project = get_object_or_404(Project, slug=slug)

    if not project.is_public:
        if not request.user.is_authenticated:
            raise Http404("Project is private.")
        if not Membership.objects.filter(project=project, user=request.user).exists():
            raise Http404("Project is private.")

    snapshot = get_latest_published_snapshot(project)
    manifest = snapshot.manifest_data if snapshot else None

    grouped_credits = {}
    if manifest:
        for c in manifest.get("credits", []):
            dept = c.get("department_name", "General")
            if dept not in grouped_credits:
                grouped_credits[dept] = []
            grouped_credits[dept].append(c)

    return render(
        request,
        "public/public_credit_roll.html",
        {
            "project": project,
            "snapshot": snapshot,
            "manifest": manifest,
            "grouped_credits": grouped_credits,
        },
    )


def public_contributor_profile_view(request, handle):
    clean_handle = handle if handle.startswith("@") else f"@{handle}"
    memberships = Membership.objects.filter(
        public_handle__iexact=clean_handle, public_credit_opt_in=True
    ).select_related("project", "user")

    if not memberships.exists():
        raise Http404("Contributor profile not found or private.")

    first_mem = memberships.first()
    portfolio_links = first_mem.portfolio_links

    # Aggregate contributions across public projects
    public_contributions = []
    for m in memberships:
        if m.project.is_public:
            snapshot = get_latest_published_snapshot(m.project)
            if snapshot:
                for c in snapshot.manifest_data.get("credits", []):
                    if c.get("credited_name") == m.credited_name:
                        public_contributions.append({
                            "project_name": m.project.name,
                            "project_slug": m.project.slug,
                            "role_name": c.get("role_name"),
                            "department_name": c.get("department_name"),
                            "basis": c.get("basis"),
                            "summary": c.get("contribution_summary"),
                        })

    return render(
        request,
        "public/public_contributor.html",
        {
            "credited_name": first_mem.credited_name,
            "public_handle": clean_handle,
            "portfolio_links": portfolio_links,
            "public_contributions": public_contributions,
        },
    )


@login_required
def publish_snapshot_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        title = request.POST.get("snapshot_title", "")
        try:
            snapshot = publish_project_provenance_snapshot(
                project=project, actor_membership=actor_membership, title=title
            )
            messages.success(request, f"Provenance Snapshot v{snapshot.version_number} published successfully!")
            return redirect("public_project", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return redirect("production_room", slug=project.slug)


def export_json_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    snapshot = get_latest_published_snapshot(project)

    if not snapshot or not project.is_public:
        raise Http404("No published provenance snapshot available.")

    content = export_credits_json(snapshot)
    response = HttpResponse(content, content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{project.slug}_provenance_v{snapshot.version_number}.json"'
    return response


def export_csv_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    snapshot = get_latest_published_snapshot(project)

    if not snapshot or not project.is_public:
        raise Http404("No published provenance snapshot available.")

    content = export_credits_csv(snapshot)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{project.slug}_credits_v{snapshot.version_number}.csv"'
    return response


def export_print_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    snapshot = get_latest_published_snapshot(project)

    if not snapshot or not project.is_public:
        raise Http404("No published provenance snapshot available.")

    manifest = snapshot.manifest_data
    grouped_credits = {}
    for c in manifest.get("credits", []):
        dept = c.get("department_name", "General")
        if dept not in grouped_credits:
            grouped_credits[dept] = []
        grouped_credits[dept].append(c)

    return render(
        request,
        "public/print_credit_roll.html",
        {"project": project, "snapshot": snapshot, "manifest": manifest, "grouped_credits": grouped_credits},
    )


def manifest_json_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    snapshot = get_latest_published_snapshot(project)

    if not snapshot or not project.is_public:
        return JsonResponse({"error": "No published provenance snapshot found for this project."}, status=404)

    return JsonResponse(snapshot.manifest_data)
