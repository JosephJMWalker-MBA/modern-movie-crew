from apps.production.models import ProductionTask
from services.boundary_services import verify_membership_in_project


def find_eligible_open_tasks_for_contributor(
    *,
    membership,
    asset_types: list = None,
    tools: list = None,
    department_id: int = None,
    scene_id: int = None,
    character_id: int = None,
    claimed_filter: str = "all",  # "all", "unclaimed", "claimed"
):
    """
    Finds open production tasks matching contributor preferences/filters.
    NON-MUTATING: Pure query read function. Does NOT mutate task or claim state!
    """
    verify_membership_in_project(membership=membership, project=membership.project)

    qs = ProductionTask.objects.filter(
        project=membership.project, status=ProductionTask.Status.OPEN
    ).select_related("scene", "project").prefetch_related("packet_sections", "claims", "character_links")

    if asset_types:
        qs = qs.filter(task_type__in=asset_types)

    if department_id:
        qs = qs.filter(packet_sections__department_id=department_id)

    if scene_id:
        qs = qs.filter(scene_id=scene_id)

    if character_id:
        qs = qs.filter(character_links__character_id=character_id)

    if claimed_filter == "unclaimed":
        qs = qs.exclude(claims__status="active")
    elif claimed_filter == "claimed":
        qs = qs.filter(claims__status="active")

    return qs.distinct()
