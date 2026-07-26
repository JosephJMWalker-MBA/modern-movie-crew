from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.shortcuts import get_object_or_404, redirect, render

from apps.production.models import ProductionTask
from apps.projects.models import Membership, MembershipAgreement, Project
from apps.submissions.models import Submission, SubmissionVersion
from services.review_services import accept_submission_version
from services.submission_services import (
    create_submission_v2,
    create_submission_with_v1,
    request_submission_revision,
    submit_department_review,
)


@login_required
def upload_v1_view(request, slug, task_id):
    project = get_object_or_404(Project, slug=slug)
    task = get_object_or_404(ProductionTask, pk=task_id, project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    # Ensure terms agreement exists
    terms = project.terms_versions.first()
    if terms:
        MembershipAgreement.objects.get_or_create(membership=membership, terms_version=terms)

    if request.method == "POST":
        file_obj = request.FILES.get("media_file")
        tool = request.POST.get("external_tool", "Sora")
        prompt = request.POST.get("prompt_used", "")
        seed = request.POST.get("seed", "")

        storage_key = f"uploads/{file_obj.name}" if file_obj else "uploads/footage_v1.mp4"
        if file_obj:
            fs = FileSystemStorage()
            fs.save(storage_key, file_obj)

        try:
            version = create_submission_with_v1(
                task=task,
                contributor_membership=membership,
                storage_key=storage_key,
                file_obj=file_obj,
                external_tool=tool,
                prompt_used=prompt,
                seed=seed,
            )
            messages.success(request, f"Submission V1 uploaded successfully for {task.code}!")
            return redirect("task_detail", slug=project.slug, task_id=task.id)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "submissions/upload_v1.html", {"project": project, "task": task})


@login_required
def department_review_view(request, slug, version_id):
    project = get_object_or_404(Project, slug=slug)
    version = get_object_or_404(SubmissionVersion, pk=version_id, submission__task__project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)
    assignment = membership.role_assignments.filter(ends_at__isnull=True).first()

    if not assignment:
        messages.error(request, "Active role assignment required for department review.")
        return redirect("task_detail", slug=project.slug, task_id=version.submission.task.id)

    if request.method == "POST":
        decision = request.POST.get("decision", "approved")
        notes = request.POST.get("notes", "")

        try:
            submit_department_review(
                version=version, reviewer_assignment=assignment, decision=decision, notes=notes
            )
            messages.success(request, f"Department review ({decision}) submitted!")
        except Exception as e:
            messages.error(request, str(e))

        return redirect("task_detail", slug=project.slug, task_id=version.submission.task.id)

    return render(request, "submissions/dept_review.html", {"project": project, "version": version})


@login_required
def director_revision_view(request, slug, version_id):
    project = get_object_or_404(Project, slug=slug)
    version = get_object_or_404(SubmissionVersion, pk=version_id, submission__task__project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        notes = request.POST.get("notes", "")

        try:
            request_submission_revision(
                version=version, reviewer_membership=membership, notes=notes
            )
            messages.success(request, f"Revision requested on version {version.version_number}!")
        except Exception as e:
            messages.error(request, str(e))

        return redirect("task_detail", slug=project.slug, task_id=version.submission.task.id)

    return render(request, "submissions/director_revision.html", {"project": project, "version": version})


@login_required
def upload_v2_view(request, slug, submission_id):
    project = get_object_or_404(Project, slug=slug)
    submission = get_object_or_404(Submission, pk=submission_id, task__project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        file_obj = request.FILES.get("media_file")
        tool = request.POST.get("external_tool", "Sora")
        prompt = request.POST.get("prompt_used", "")
        seed = request.POST.get("seed", "")

        storage_key = f"uploads/{file_obj.name}" if file_obj else "uploads/footage_v2.mp4"
        if file_obj:
            fs = FileSystemStorage()
            fs.save(storage_key, file_obj)

        try:
            version = create_submission_v2(
                submission=submission,
                contributor_membership=membership,
                storage_key=storage_key,
                file_obj=file_obj,
                external_tool=tool,
                prompt_used=prompt,
                seed=seed,
            )
            messages.success(request, f"Submission V2 uploaded for {submission.task.code}!")
            return redirect("task_detail", slug=project.slug, task_id=submission.task.id)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "submissions/upload_v2.html", {"project": project, "submission": submission})


@login_required
def director_accept_view(request, slug, version_id):
    project = get_object_or_404(Project, slug=slug)
    version = get_object_or_404(SubmissionVersion, pk=version_id, submission__task__project=project)
    membership = get_object_or_404(Membership, project=project, user=request.user)

    if request.method == "POST":
        notes = request.POST.get("notes", "")

        try:
            accept_submission_version(
                version=version, reviewer_membership=membership, notes=notes
            )
            messages.success(request, f"Version {version.version_number} ACCEPTED as Canonical Asset!")
        except Exception as e:
            messages.error(request, str(e))

        return redirect("task_detail", slug=project.slug, task_id=version.submission.task.id)

    return render(request, "submissions/director_accept.html", {"project": project, "version": version})
