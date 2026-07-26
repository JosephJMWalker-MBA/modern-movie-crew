from django.db import transaction
from django.utils.text import slugify

from apps.core.models import AuditEvent
from apps.projects.models import (
    Department,
    Membership,
    MembershipAgreement,
    ProductionRole,
    Project,
    ProjectTermsVersion,
    RoleAssignment,
)
from services.boundary_services import verify_director_authority, verify_membership_in_project


@transaction.atomic
def seed_default_safe_roles_for_project(*, project: Project):
    """Seeds default non-privileged contributor roles that pass is_safe_invite_role()."""
    gen_dept = project.departments.filter(name="Generation Department").first()
    art_dept = project.departments.filter(name="Art Department").first() or project.departments.first()

    if not gen_dept and art_dept:
        gen_dept = art_dept

    if gen_dept:
        ProductionRole.objects.get_or_create(
            project=project,
            name="Generation Contributor",
            defaults={
                "department": gen_dept,
                "can_assign_tasks": False,
                "can_approve_department_work": False,
                "can_accept_final_assets": False,
                "can_manage_credits": False,
            },
        )

    if art_dept:
        ProductionRole.objects.get_or_create(
            project=project,
            name="Art Contributor",
            defaults={
                "department": art_dept,
                "can_assign_tasks": False,
                "can_approve_department_work": False,
                "can_accept_final_assets": False,
                "can_manage_credits": False,
            },
        )


@transaction.atomic
def create_project_with_defaults(
    *, creator_user, name: str, synopsis: str = ""
) -> Project:
    slug = slugify(name)
    project = Project.objects.create(
        name=name, slug=slug, synopsis=synopsis, created_by=creator_user
    )

    terms = ProjectTermsVersion.objects.create(
        project=project,
        version_number=1,
        terms_text="Standard Modern Movie Crew Project Terms v1",
    )

    # Initial departments
    dir_dept = Department.objects.create(project=project, name="Direction Department", sort_order=0)
    art_dept = Department.objects.create(project=project, name="Art Department", sort_order=1)
    costume_dept = Department.objects.create(project=project, name="Costume Department", sort_order=2)
    gen_dept = Department.objects.create(project=project, name="Generation Department", sort_order=3)

    # Initial Director Role (privileged)
    director_role = ProductionRole.objects.create(
        project=project,
        department=dir_dept,
        name="Director",
        can_assign_tasks=True,
        can_approve_department_work=True,
        can_accept_final_assets=True,
        can_manage_credits=True,
    )

    # Seed initial non-privileged contributor roles (safe for invites)
    seed_default_safe_roles_for_project(project=project)

    membership = Membership.objects.create(
        project=project,
        user=creator_user,
        credited_name=creator_user.display_name or creator_user.username,
        status=Membership.Status.ACTIVE,
    )

    MembershipAgreement.objects.create(membership=membership, terms_version=terms)

    RoleAssignment.objects.create(
        membership=membership, role=director_role, is_department_head=True
    )

    AuditEvent.objects.create(
        project=project,
        actor=membership,
        event_type="project_created",
        object_type="project",
        object_id=str(project.id),
        metadata={"project_name": name},
    )

    return project


@transaction.atomic
def add_crew_member_with_role(
    *, project: Project, actor_membership: Membership, target_user, credited_name: str, role: ProductionRole
) -> Membership:
    verify_director_authority(reviewer=actor_membership, project=project)

    if role.project_id != project.id:
        raise ValueError("ProductionRole does not belong to the target project.")

    terms = project.terms_versions.order_by("-version_number").first()

    membership = Membership.objects.create(
        project=project,
        user=target_user,
        credited_name=credited_name,
        status=Membership.Status.ACTIVE,
    )

    if terms:
        MembershipAgreement.objects.create(membership=membership, terms_version=terms)

    RoleAssignment.objects.create(
        membership=membership, role=role, is_department_head=False
    )

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="crew_member_added",
        object_type="membership",
        object_id=str(membership.id),
        metadata={"credited_name": credited_name, "role_name": role.name},
    )

    return membership
