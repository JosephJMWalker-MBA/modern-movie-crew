import csv
import io
import json
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.credits.models import CreditEntry, ProjectProvenanceSnapshot
from apps.projects.models import Project
from services.boundary_services import verify_director_authority, verify_membership_in_project

DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(val: str) -> str:
    """Prevents CSV formula injection by prepending a single quote if string starts with dangerous characters."""
    if not val:
        return ""
    val_str = str(val)
    if val_str.startswith(DANGEROUS_CSV_PREFIXES):
        return f"'{val_str}"
    return val_str


@transaction.atomic
def publish_project_provenance_snapshot(
    *,
    project: Project,
    actor_membership,
    title: str = "",
) -> ProjectProvenanceSnapshot:
    """
    Creates an immutable published provenance snapshot for a project.
    EXPLICIT ALLOWLIST OF PUBLIC FIELDS ONLY.
    Excludes rejected work, private reviews, rights attestations, tokens, and file storage paths.
    Uses select_for_update on the project to prevent concurrent version numbering race conditions.
    """
    verify_director_authority(reviewer=actor_membership, project=project)

    # Lock project row to prevent concurrent publication race conditions
    locked_project = Project.objects.select_for_update().get(pk=project.pk)

    next_version_num = (
        locked_project.provenance_snapshots.order_by("-version_number").first().version_number + 1
        if locked_project.provenance_snapshots.exists()
        else 1
    )

    locked_project.provenance_snapshots.filter(retired_at__isnull=True).update(retired_at=timezone.now())

    eligible_credits = (
        CreditEntry.objects.filter(
            project=locked_project,
            status=CreditEntry.Status.ELIGIBLE,
            contributor__public_credit_opt_in=True,
        )
        .select_related("contributor")
        .order_by("department_name", "role_name", "credited_name")
    )

    public_credits_list = []
    contributor_handles = set()

    for c in eligible_credits:
        public_credits_list.append({
            "credited_name": c.credited_name,
            "public_handle": c.contributor.public_handle or "",
            "role_name": c.role_name,
            "department_name": c.department_name,
            "basis": c.basis,
            "is_final_cut": c.is_final_cut,
            "contribution_summary": c.contribution_summary,
        })
        if c.contributor.public_handle:
            contributor_handles.add(c.contributor.public_handle)

    accepted_tasks = locked_project.tasks.filter(
        canonical_selections__retired_at__isnull=True
    ).prefetch_related("canonical_selections__submission_version__created_by")

    public_assets_list = []
    for t in accepted_tasks:
        active_sel = t.active_canonical_selection()
        if active_sel:
            version = active_sel.submission_version
            contributor_name = (
                version.created_by.credited_name
                if version.created_by.public_credit_opt_in
                else "Verified Contributor"
            )
            public_assets_list.append({
                "task_code": t.code,
                "task_title": t.title,
                "task_type": t.task_type,
                "version_number": version.version_number,
                "external_tool": version.external_tool,
                "contributor_name": contributor_name,
                "selected_at": active_sel.selected_at.isoformat(),
            })

    departments_list = list(
        locked_project.departments.values_list("name", flat=True)
    )

    manifest = {
        "manifest_version": "1.0",
        "published_at": timezone.now().isoformat(),
        "project": {
            "name": locked_project.name,
            "slug": locked_project.slug,
            "synopsis": locked_project.synopsis,
            "status": locked_project.status,
            "poster_image": locked_project.poster_image or "",
            "final_film_url": locked_project.final_film_url or "",
            "is_public": locked_project.is_public,
        },
        "summary": {
            "verified_contributor_count": len(contributor_handles) or len(public_credits_list),
            "accepted_asset_count": len(public_assets_list),
            "department_count": len(departments_list),
        },
        "departments": departments_list,
        "credits": public_credits_list,
        "accepted_assets": public_assets_list,
    }

    snapshot = ProjectProvenanceSnapshot.objects.create(
        project=locked_project,
        version_number=next_version_num,
        published_by=actor_membership,
        snapshot_title=title or f"Publication Snapshot v{next_version_num}",
        manifest_data=manifest,
    )

    AuditEvent.objects.create(
        project=locked_project,
        actor=actor_membership,
        event_type="provenance_snapshot_published",
        object_type="project_provenance_snapshot",
        object_id=str(snapshot.id),
        metadata={"version_number": next_version_num},
    )

    return snapshot


def get_latest_published_snapshot(project: Project) -> ProjectProvenanceSnapshot:
    """Returns the latest active published ProjectProvenanceSnapshot for a project, or None."""
    return project.provenance_snapshots.filter(retired_at__isnull=True).order_by("-version_number").first()


def export_credits_json(snapshot: ProjectProvenanceSnapshot) -> str:
    """Generates formatted JSON string from a published provenance snapshot."""
    return json.dumps(snapshot.manifest_data, indent=2)


def export_credits_csv(snapshot: ProjectProvenanceSnapshot) -> str:
    """Generates CSV string of public credits with CSV formula injection protection."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Credited Name",
        "Public Handle",
        "Role",
        "Department",
        "Basis",
        "Final Cut",
        "Summary",
    ])

    credits_list = snapshot.manifest_data.get("credits", [])
    for c in credits_list:
        writer.writerow([
            sanitize_csv_cell(c.get("credited_name", "")),
            sanitize_csv_cell(c.get("public_handle", "")),
            sanitize_csv_cell(c.get("role_name", "")),
            sanitize_csv_cell(c.get("department_name", "")),
            sanitize_csv_cell(c.get("basis", "")),
            "Yes" if c.get("is_final_cut") else "No",
            sanitize_csv_cell(c.get("contribution_summary", "")),
        ])

    return output.getvalue()
