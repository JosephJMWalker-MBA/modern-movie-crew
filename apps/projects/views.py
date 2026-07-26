import re
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import URLValidator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render

from apps.production.models import ProductionTask, TaskClaim
from apps.projects.models import (
    Department,
    Membership,
    ProductionRole,
    Project,
    ProjectInviteToken,
)
from apps.submissions.models import CanonicalSelection, Submission
from services.invite_services import (
    accept_project_invite,
    create_project_invite,
    revoke_project_invite,
)
from services.matching_services import find_eligible_open_tasks_for_contributor
from services.project_services import add_crew_member_with_role, create_project_with_defaults

CONTROLLED_ASSET_TYPES = {"video", "voice", "sound", "image"}
CONTROLLED_TOOLS = {
    "sora", "runway", "veo", "kling", "pika", "elevenlabs", "suno", "midjourney",
    "stable diffusion", "flux", "custom model"
}

url_validator = URLValidator(schemes=["http", "https"])


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
            return redirect("production_room", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "projects/create_project.html")


@login_required
def project_detail_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    memberships = project.memberships.select_related("user").all()
    departments = project.departments.prefetch_related("roles").all()
    invites = project.invite_tokens.all()

    user_membership = memberships.filter(user=request.user).first()

    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "memberships": memberships,
            "departments": departments,
            "user_membership": user_membership,
            "invites": invites,
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


@login_required
def production_room_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    user_membership = get_object_or_404(Membership, project=project, user=request.user)

    # Exclude cancelled & draft tasks from active progress calculations
    active_tasks = project.tasks.exclude(status__in=[ProductionTask.Status.CANCELLED, ProductionTask.Status.DRAFT])
    total_active = active_tasks.count()
    satisfied_tasks = active_tasks.filter(status=ProductionTask.Status.SATISFIED).count()
    progress_percent = int((satisfied_tasks / total_active * 100)) if total_active > 0 else 0

    open_tasks = project.tasks.filter(status=ProductionTask.Status.OPEN).select_related("scene").order_by("code", "id")
    claimed_claims = TaskClaim.objects.filter(task__project=project, status=TaskClaim.Status.ACTIVE).select_related("task", "contributor").order_by("-claimed_at", "id")
    awaiting_reviews = Submission.objects.filter(task__project=project, status=Submission.Status.IN_REVIEW).select_related("task", "contributor").order_by("-created_at", "id")
    revision_requests = Submission.objects.filter(task__project=project, status=Submission.Status.REVISION_REQUESTED).select_related("task", "contributor").order_by("-created_at", "id")
    recent_canonicals = CanonicalSelection.objects.filter(task__project=project, retired_at__isnull=True).select_related("task", "submission_version", "selected_by").order_by("-selected_at", "id")[:5]

    # Stable pagination for open tasks
    paginator = Paginator(open_tasks, 10)
    page_number = request.GET.get("page", 1)
    open_tasks_page = paginator.get_page(page_number)

    return render(
        request,
        "projects/production_room.html",
        {
            "project": project,
            "user_membership": user_membership,
            "total_tasks": total_active,
            "satisfied_tasks": satisfied_tasks,
            "progress_percent": progress_percent,
            "open_tasks_page": open_tasks_page,
            "claimed_claims": claimed_claims,
            "awaiting_reviews": awaiting_reviews,
            "revision_requests": revision_requests,
            "recent_canonicals": recent_canonicals,
        },
    )


@login_required
def create_invite_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        role_id = request.POST.get("role_id")
        duration_days = int(request.POST.get("duration_days", 7))
        max_uses = int(request.POST.get("max_uses", 5))

        default_role = get_object_or_404(ProductionRole, pk=role_id, project=project)

        try:
            invite = create_project_invite(
                project=project,
                actor_membership=actor_membership,
                default_role=default_role,
                duration_days=duration_days,
                max_uses=max_uses,
            )
            messages.success(request, f"Invite link created for role {default_role.name}!")
            return redirect("project_detail", slug=project.slug)
        except Exception as e:
            messages.error(request, str(e))

    roles = [r for r in ProductionRole.objects.filter(project=project) if r.is_safe_invite_role()]
    return render(request, "projects/create_invite.html", {"project": project, "roles": roles})


@login_required
def revoke_invite_view(request, slug, invite_id):
    project = get_object_or_404(Project, slug=slug)
    invite = get_object_or_404(ProjectInviteToken, pk=invite_id, project=project)
    actor_membership = get_object_or_404(Membership, project=project, user=request.user)

    try:
        revoke_project_invite(invite_token=invite, actor_membership=actor_membership)
        messages.success(request, "Invite link revoked!")
    except Exception as e:
        messages.error(request, str(e))

    return redirect("project_detail", slug=project.slug)


@login_required
def accept_invite_view(request, token_str):
    invite = get_object_or_404(ProjectInviteToken, token=str(token_str).strip())

    if request.method == "POST":
        credited_name = request.POST.get("credited_name", "")

        try:
            membership = accept_project_invite(
                token_str=token_str, user=request.user, credited_name=credited_name
            )
            messages.success(request, f"Welcome to {membership.project.name}!")
            return redirect("production_room", slug=membership.project.slug)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "projects/accept_invite.html", {"invite": invite})


@login_required
def spare_gen_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    user_membership = get_object_or_404(Membership, project=project, user=request.user)

    asset_type = request.GET.get("asset_type", "").strip().lower()
    dept_id = request.GET.get("department_id", "")
    claimed_filter = request.GET.get("claimed", "all")

    asset_types = [asset_type] if asset_type in CONTROLLED_ASSET_TYPES else None
    department_id = int(dept_id) if dept_id and dept_id.isdigit() else None

    # NON-MUTATING QUERY WITH STABLE ORDERING
    eligible_tasks = find_eligible_open_tasks_for_contributor(
        membership=user_membership,
        asset_types=asset_types,
        department_id=department_id,
        claimed_filter=claimed_filter,
    ).order_by("code", "id")

    paginator = Paginator(eligible_tasks, 12)
    page_number = request.GET.get("page", 1)
    tasks_page = paginator.get_page(page_number)

    departments = project.departments.all()

    return render(
        request,
        "projects/spare_gen.html",
        {
            "project": project,
            "user_membership": user_membership,
            "tasks_page": tasks_page,
            "departments": departments,
            "selected_asset_type": asset_type,
            "selected_dept": dept_id,
            "selected_claimed": claimed_filter,
        },
    )


@login_required
def edit_profile_view(request, slug):
    project = get_object_or_404(Project, slug=slug)
    user_membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        credited_name = request.POST.get("credited_name", "").strip()
        public_handle = request.POST.get("public_handle", "").strip()
        tools_input = request.POST.get("available_tools", "")
        asset_types_input = request.POST.get("supported_asset_types", "")
        portfolio_input = request.POST.get("portfolio_links", "")

        # Handle validation
        if public_handle:
            if not re.match(r"^@?[a-zA-Z0-9_-]{2,50}$", public_handle):
                messages.error(request, "Public handle must be 2-50 alphanumeric characters (underscores and dashes allowed).")
                return render(request, "projects/edit_profile.html", {"project": project, "membership": user_membership})
            if not public_handle.startswith("@"):
                public_handle = f"@{public_handle}"

        # Portfolio URL validation
        portfolio_urls = [p.strip() for p in portfolio_input.split(",") if p.strip()]
        for url in portfolio_urls:
            try:
                url_validator(url)
            except ValidationError:
                messages.error(request, f"Invalid portfolio URL scheme or syntax: '{url}'. Links must use http:// or https://")
                return render(request, "projects/edit_profile.html", {"project": project, "membership": user_membership})

        # Controlled normalization
        raw_tools = [t.strip().lower() for t in tools_input.split(",") if t.strip()]
        normalized_tools = [t for t in raw_tools if t in CONTROLLED_TOOLS or len(t) <= 30]

        raw_assets = [a.strip().lower() for a in asset_types_input.split(",") if a.strip()]
        normalized_assets = [a for a in raw_assets if a in CONTROLLED_ASSET_TYPES]

        user_membership.credited_name = credited_name or user_membership.credited_name
        user_membership.public_handle = public_handle
        user_membership.available_tools = normalized_tools
        user_membership.supported_asset_types = normalized_assets
        user_membership.portfolio_links = portfolio_urls
        user_membership.save()

        messages.success(request, "Contributor profile updated successfully!")
        return redirect("production_room", slug=project.slug)

    return render(
        request,
        "projects/edit_profile.html",
        {"project": project, "membership": user_membership},
    )
