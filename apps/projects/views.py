from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.models import (
    Department,
    Membership,
    ProductionRole,
    Project,
)
from services.project_services import add_crew_member_with_role, create_project_with_defaults

User = get_user_model()


@login_required
def create_project_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        synopsis = request.POST.get("synopsis", "")

        try:
            project = create_project_with_defaults(
                creator_user=request.user, name=name, synopsis=synopsis
            )
            messages.success(request, f"Project '{name}' created successfully!")
            return redirect("project_detail", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "projects/create_project.html")


@login_required
def project_detail_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    memberships = project.memberships.select_related("user").all()
    departments = project.departments.prefetch_related("roles").all()

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
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        credited_name = request.POST.get("credited_name")
        role_id = request.POST.get("role_id")
        role = get_object_or_404(ProductionRole, pk=role_id, project=project)

        try:
            add_crew_member_with_role(
                project=project,
                actor_membership=actor_membership,
                target_user=request.user,
                credited_name=credited_name,
                role=role,
            )
            messages.success(request, f"Crew member '{credited_name}' added as {role.name}!")
            return redirect("project_detail", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    roles = ProductionRole.objects.filter(project=project)
    return render(request, "projects/add_crew.html", {"project": project, "roles": roles})
