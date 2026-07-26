from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.models import UserFeedback
from apps.projects.models import Membership, Project
from services.feedback_services import submit_user_feedback, triage_user_feedback


@login_required
def submit_feedback_view(request):
    if request.method == "POST":
        category = request.POST.get("category", UserFeedback.Category.WORKFLOW_IMPROVEMENT)
        title = request.POST.get("title", "").strip()
        what_user_was_doing = request.POST.get("what_user_was_doing", "").strip()
        actual_result = request.POST.get("actual_result", "").strip()
        ideal_result = request.POST.get("ideal_result", "").strip()
        severity = request.POST.get("severity", UserFeedback.Severity.MEDIUM)

        page_url = request.POST.get("page_url") or request.META.get("HTTP_REFERER", "/")
        page_name = request.POST.get("page_name", "Application Page")
        context_type = request.POST.get("context_type", "")
        context_identifier = request.POST.get("context_identifier", "")

        project_id = request.POST.get("project_id")
        project = Project.objects.filter(pk=project_id).first() if project_id else None

        user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            feedback = submit_user_feedback(
                user=request.user,
                page_url=page_url,
                page_name=page_name,
                category=category,
                title=title,
                what_user_was_doing=what_user_was_doing,
                actual_result=actual_result,
                ideal_result=ideal_result,
                severity=severity,
                project=project,
                context_type=context_type,
                context_identifier=context_identifier,
                user_agent=user_agent,
            )
            messages.success(
                request,
                f"Thank you! Your feedback #{feedback.id} ('{feedback.title}') has been received by our development team."
            )
        except Exception as e:
            messages.error(request, str(e))

        return redirect(page_url)

    return redirect("dashboard")


@login_required
def my_feedback_view(request):
    user_entries = UserFeedback.objects.filter(submitted_by=request.user).select_related("project", "duplicate_of").order_by("-created_at")
    return render(
        request,
        "feedback/my_feedback.html",
        {"user_entries": user_entries},
    )


@login_required
def feedback_inbox_view(request):
    if not request.user.is_staff:
        # Check if user is a Director on any project
        is_director = Membership.objects.filter(
            user=request.user,
            role_assignments__role__can_accept_final_assets=True,
            role_assignments__ends_at__isnull=True,
        ).exists()
        if not is_director:
            raise PermissionDenied("Access to internal feedback inbox is restricted to staff and project directors.")

    category = request.GET.get("category")
    status = request.GET.get("status")
    severity = request.GET.get("severity")
    project_id = request.GET.get("project_id")

    qs = UserFeedback.objects.select_related("submitted_by", "project", "duplicate_of").all()

    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)
    if severity:
        qs = qs.filter(severity=severity)
    if project_id:
        qs = qs.filter(project_id=project_id)

    projects = Project.objects.all()

    return render(
        request,
        "feedback/feedback_inbox.html",
        {
            "feedback_list": qs,
            "projects": projects,
            "filters": {
                "category": category,
                "status": status,
                "severity": severity,
                "project_id": project_id,
            },
        },
    )


@login_required
def feedback_detail_view(request, feedback_id):
    feedback = get_object_or_404(UserFeedback, pk=feedback_id)

    if request.method == "POST":
        status = request.POST.get("status")
        internal_notes = request.POST.get("internal_notes")
        dup_id = request.POST.get("duplicate_of_id")
        gh_num = request.POST.get("github_issue_number")
        gh_url = request.POST.get("github_issue_url", "").strip()

        duplicate_of = UserFeedback.objects.filter(pk=dup_id).first() if dup_id else None
        github_issue_number = int(gh_num) if gh_num and gh_num.isdigit() else None

        try:
            triage_user_feedback(
                feedback=feedback,
                actor_user=request.user,
                status=status,
                internal_notes=internal_notes,
                duplicate_of=duplicate_of,
                github_issue_number=github_issue_number,
                github_issue_url=gh_url,
            )
            messages.success(request, f"Feedback #{feedback.id} updated successfully.")
            return redirect("feedback_detail", feedback_id=feedback.id)
        except Exception as e:
            messages.error(request, str(e))

    all_feedback_options = UserFeedback.objects.exclude(pk=feedback.id).order_by("-id")[:100]

    return render(
        request,
        "feedback/feedback_detail.html",
        {
            "feedback": feedback,
            "all_feedback_options": all_feedback_options,
        },
    )
