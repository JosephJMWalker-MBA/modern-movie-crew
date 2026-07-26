from django.core.exceptions import PermissionDenied


def verify_membership_in_project(*, membership, project):
    if membership.project_id != project.id:
        raise PermissionDenied(
            f"Membership {membership.id} does not belong to Project {project.id}."
        )


def verify_active_role_assignment(*, assignment):
    if not assignment.is_active():
        raise PermissionDenied(
            f"Role assignment {assignment.id} is no longer active."
        )


def verify_role_in_project(*, role, project):
    if role.project_id != project.id:
        raise PermissionDenied(
            f"ProductionRole {role.id} does not belong to Project {project.id}."
        )


def verify_department_match(*, assignment, target_department):
    # Mandatory project boundary check
    verify_membership_in_project(
        membership=assignment.membership,
        project=target_department.project,
    )

    # Director / final asset authority grants cross-department super-admin authority within the project
    if assignment.role.can_accept_final_assets:
        return

    if assignment.role.department_id != target_department.id:
        raise PermissionDenied(
            f"Role {assignment.role.name} in department {assignment.role.department.name} "
            f"cannot act on department {target_department.name}."
        )


def verify_director_authority(*, reviewer, project):
    verify_membership_in_project(membership=reviewer, project=project)
    active_assignments = reviewer.role_assignments.filter(ends_at__isnull=True)
    has_director_permission = active_assignments.filter(
        role__can_accept_final_assets=True,
        role__project=project,
    ).exists()
    if not has_director_permission:
        raise PermissionDenied(
            f"Member {reviewer.credited_name} does not hold final acceptance authority for project {project.name}."
        )
