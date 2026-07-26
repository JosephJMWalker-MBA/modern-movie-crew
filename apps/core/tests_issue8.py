from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import UserFeedback
from services.feedback_services import submit_user_feedback, triage_user_feedback
from services.project_services import create_project_with_defaults

User = get_user_model()


class Issue8UserFeedbackTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_creator = User.objects.create_user(username="fb_creator", password="Password123!")
        self.user_member = User.objects.create_user(username="fb_member", password="Password123!")
        self.user_outsider = User.objects.create_user(username="fb_outsider", password="Password123!")

        self.project_a = create_project_with_defaults(
            creator_user=self.user_creator, name="Feedback Film A", synopsis="Project A"
        )
        self.membership_creator = self.project_a.memberships.get(user=self.user_creator)

    def test_submit_contextual_user_feedback(self):
        fb = submit_user_feedback(
            user=self.user_creator,
            page_url="/projects/fb-film-a/script/",
            page_name="Script Workspace",
            category="workflow_improvement",
            title="Auto-link character suggestions",
            what_user_was_doing="I was reviewing screenplay dialogue line by line.",
            ideal_result="I want candidate speaker names to auto-link to existing character identity records.",
            actual_result="Candidate names appeared as unlinked text.",
            severity="medium",
            project=self.project_a,
            context_type="script_segment",
            context_identifier="12",
            user_agent="Mozilla/5.0 TestBrowser/1.0",
        )

        self.assertIsInstance(fb, UserFeedback)
        self.assertEqual(fb.title, "Auto-link character suggestions")
        self.assertEqual(fb.ideal_result, "I want candidate speaker names to auto-link to existing character identity records.")
        self.assertEqual(fb.context_snapshot.get("user_agent"), "Mozilla/5.0 TestBrowser/1.0")
        self.assertEqual(fb.context_snapshot.get("project_slug"), self.project_a.slug)
        self.assertEqual(fb.status, UserFeedback.Status.NEW)

    def test_metadata_allowlisting_prevents_sensitive_data_leakage(self):
        fb = submit_user_feedback(
            user=self.user_creator,
            page_url="/projects/fb-film-a/",
            page_name="Project Detail",
            category="bug",
            title="UI Alignment",
            what_user_was_doing="Viewing board",
            ideal_result="Card padding aligned",
            extra_context={
                "screen_resolution": "1920x1080",
                "secret_cookie_token": "SENSITIVE_SESSION_KEY_12345",  # Disallowed
                "authorization_header": "Bearer secret_jwt_token",      # Disallowed
            },
        )

        self.assertIn("screen_resolution", fb.context_snapshot)
        self.assertNotIn("secret_cookie_token", fb.context_snapshot)
        self.assertNotIn("authorization_header", fb.context_snapshot)

    def test_cross_project_feedback_isolation_denied(self):
        with self.assertRaises(PermissionDenied):
            submit_user_feedback(
                user=self.user_outsider,
                page_url="/projects/fb-film-a/",
                page_name="Private Project",
                category="bug",
                title="Unauthorized feedback",
                what_user_was_doing="Browsing private project",
                ideal_result="Access denied",
                project=self.project_a,
            )

    def test_rate_limiting_protection(self):
        for i in range(10):
            submit_user_feedback(
                user=self.user_creator,
                page_url="/test/",
                page_name="Test Page",
                category="other",
                title=f"Submission {i}",
                what_user_was_doing="Testing rate limit",
                ideal_result="Ideal result text",
            )

        # 11th submission within 5 minutes raises ValidationError
        with self.assertRaises(ValidationError):
            submit_user_feedback(
                user=self.user_creator,
                page_url="/test/",
                page_name="Test Page",
                category="other",
                title="Spam submission",
                what_user_was_doing="Excess submission",
                ideal_result="Exceed limit",
            )

    def test_inbox_triage_and_duplicate_grouping(self):
        fb1 = submit_user_feedback(
            user=self.user_creator,
            page_url="/test/",
            page_name="Test Page",
            category="bug",
            title="Original bug report",
            what_user_was_doing="Doing work",
            ideal_result="Fix bug",
            project=self.project_a,
        )

        fb2 = submit_user_feedback(
            user=self.user_creator,
            page_url="/test/",
            page_name="Test Page",
            category="bug",
            title="Duplicate bug report",
            what_user_was_doing="Doing same work",
            ideal_result="Fix same bug",
            project=self.project_a,
        )

        # Triage fb2 as duplicate of fb1 and link to GitHub issue #8
        triaged_fb2 = triage_user_feedback(
            feedback=fb2,
            actor_user=self.user_creator,  # Director on project_a
            status=UserFeedback.Status.DUPLICATE,
            duplicate_of=fb1,
            github_issue_number=8,
            github_issue_url="https://github.com/JosephJMWalker-MBA/modern-movie-crew/issues/8",
            internal_notes="Grouped duplicate with original issue #8",
        )

        self.assertEqual(triaged_fb2.status, UserFeedback.Status.DUPLICATE)
        self.assertEqual(triaged_fb2.duplicate_of, fb1)
        self.assertEqual(triaged_fb2.github_issue_number, 8)
        self.assertIn("Grouped duplicate", triaged_fb2.internal_notes)

    def test_unauthorized_user_cannot_access_inbox(self):
        self.client.force_login(self.user_outsider)
        resp = self.client.get(reverse("feedback_inbox"))
        self.assertEqual(resp.status_code, 403)
