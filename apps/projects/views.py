from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from apps.projects.models import (
    Department,
    Membership,
    ProductionRole,
    Project,
    ProjectTermsVersion,
    RoleAssignment,
)


@login_required
def create_project_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        synopsis = request.POST.get("synopsis", "")
        slug = slugify(name)

        project = Project.objects.create(
            name=name, slug=slug, synopsis=synopsis, created_by=request.user
        )

        # Create initial ProjectTermsVersion
        terms = ProjectTermsVersion.objects.create(
            project=project,
            version_number=1,
            terms_text="Standard Modern Movie Crew Project Terms v1",
        )

        # Create Director & Contributor memberships/departments
        art_dept = Department.objects.create(project=project, name="Art Department", sort_order=1)
        costume_dept = Department.objects.create(project=project, name="Costume Department", sort_order=2)
        dir_dept = Department.objects.create(project=project, name="Direction Department", sort_order=0)

        director_role = ProductionRole.objects.create(
            project=project,
            department=dir_dept,
            name="Director",
            can_assign_tasks=True,
            can_approve_department_work=True,
            can_accept_final_assets=True,
            can_manage_credits=True,
        )

        membership = Membership.objects.create(
            project=project,
            user=request.user,
            credited_name=request.user.display_name or request.user.username,
            status=Membership.Status.ACTIVE,
        )

        RoleAssignment.objects.create(
            membership=membership, role=director_role, is_department_head=True
        )

        messages.success(request, f"Project '{name}' created successfully!")
        return redirect("project_detail", slug=project.slug)

    return render(request, "projects/create_project.html")


@login_required
def project_detail_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    memberships = project.memberships.select_related("user").all()
    departments = project.departments.prefetch_related("roles").all()

    # Check current user's membership
    user_membership = memberships.filter(user=request.user).first()

    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "memberships": memberships,
            "departments": departments,
            "user_membership": user_membership,
        },
    )


@login_required
def add_crew_member_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == "POST":
        credited_name = request.POST.get("credited_name")
        role_id = request.POST.get("role_id")
        role = get_object_or_404(ProductionRole, pk=role_id, project=project)

        membership = Membership.objects.create(
            project=project,
            user=request.user,
            credited_name=credited_name,
            status=Membership.Status.ACTIVE,
        )

        RoleAssignment.objects.create(
            membership=membership, role=role, is_department_head=True
        )

        messages.success(request, f"Crew member '{credited_name}' added as {role.name}!")
        return redirect("project_detail", slug=project.slug)

    roles = ProductionRole.objects.filter(project=project)
    return render(request, "projects/add_crew.html", {"project": project, "roles": roles})
