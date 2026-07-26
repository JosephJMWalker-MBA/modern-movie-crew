from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.credits.models import CreditEntry, ProjectProvenanceSnapshot
from apps.production.models import Act, ProductionTask, Scene, Sequence
from apps.projects.models import (
    Department,
    Membership,
    ProductionRole,
    Project,
    ProjectTermsVersion,
)
from services.publication_services import (
    export_credits_csv,
    export_credits_json,
    get_latest_published_snapshot,
    publish_project_provenance_snapshot,
)

User = get_user_model()


class Milestone3PublicProvenanceTest(TestCase):
    def setUp(self):
        self.user_director = User.objects.create_user(username="director_m3", password="password")
        self.user_contributor = User.objects.create_user(username="contrib_m3", password="password")
        self.user_optout = User.objects.create_user(username="optout_m3", password="password")

        self.project = Project.objects.create(
            name="Public Movie", slug="public-movie", is_public=True, created_by=self.user_director
        )
        self.private_project = Project.objects.create(
            name="Private Movie", slug="private-movie", is_public=False, created_by=self.user_director
        )

        self.terms = ProjectTermsVersion.objects.create(project=self.project, version_number=1, terms_text="T1")
        self.dept = Department.objects.create(project=self.project, name="Generation Department")

        self.dir_role = ProductionRole.objects.create(
            project=self.project, department=self.dept, name="Director", can_accept_final_assets=True
        )
        self.gen_role = ProductionRole.objects.create(
            project=self.project, department=self.dept, name="Prompt Specialist"
        )

        self.mem_dir = Membership.objects.create(project=self.project, user=self.user_director, credited_name="Director M3")
        self.mem_dir.role_assignments.create(role=self.dir_role, is_department_head=True)

        self.mem_contrib = Membership.objects.create(
            project=self.project, user=self.user_contributor, credited_name="Gen Artist", public_handle="@gen_artist", public_credit_opt_in=True
        )
        self.mem_contrib.role_assignments.create(role=self.gen_role)

        self.mem_optout = Membership.objects.create(
            project=self.project, user=self.user_optout, credited_name="Secret User", public_credit_opt_in=False
        )
        self.mem_optout.role_assignments.create(role=self.gen_role)

        # Credit entries
        CreditEntry.objects.create(
            project=self.project,
            contributor=self.mem_contrib,
            credited_name="Gen Artist",
            role_name="Prompt Specialist",
            department_name="Generation Department",
            basis=CreditEntry.Basis.ACCEPTED_WORK,
            contribution_summary="Generated establishing shot",
        )

        CreditEntry.objects.create(
            project=self.project,
            contributor=self.mem_optout,
            credited_name="Secret User",
            role_name="Prompt Specialist",
            department_name="Generation Department",
            basis=CreditEntry.Basis.ROLE,
            contribution_summary="Hidden contribution",
        )

        self.client = Client()

    def test_unauthorized_user_cannot_publish_snapshot(self):
        # Contributor without director permission trying to publish snapshot must fail
        with self.assertRaises(PermissionDenied):
            publish_project_provenance_snapshot(
                project=self.project, actor_membership=self.mem_contrib, title="Illegal Snapshot"
            )

    def test_publish_snapshot_and_optout_privacy(self):
        snapshot = publish_project_provenance_snapshot(
            project=self.project, actor_membership=self.mem_dir, title="Official Release v1"
        )

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.version_number, 1)

        manifest = snapshot.manifest_data
        credits = manifest.get("credits", [])

        # Opted-in contributor must appear in published credits
        credited_names = [c.get("credited_name") for c in credits]
        self.assertIn("Gen Artist", credited_names)

        # Opted-out contributor must be excluded from public credits
        self.assertNotIn("Secret User", credited_names)

    def test_snapshot_immutability(self):
        snapshot = publish_project_provenance_snapshot(
            project=self.project, actor_membership=self.mem_dir, title="Immutable v1"
        )

        # Attempting to modify published snapshot must raise ValidationError
        snapshot.snapshot_title = "Edited Title"
        with self.assertRaises(ValidationError):
            snapshot.save()

        # Attempting to delete published snapshot must raise RuntimeError
        with self.assertRaises(RuntimeError):
            snapshot.delete()

    def test_superseding_snapshot(self):
        s1 = publish_project_provenance_snapshot(
            project=self.project, actor_membership=self.mem_dir, title="v1"
        )
        s2 = publish_project_provenance_snapshot(
            project=self.project, actor_membership=self.mem_dir, title="v2"
        )

        self.assertEqual(s2.version_number, 2)
        s1.refresh_from_db()
        self.assertIsNotNone(s1.retired_at)

        latest = get_latest_published_snapshot(self.project)
        self.assertEqual(latest, s2)

    def test_export_formats_use_published_snapshot(self):
        snapshot = publish_project_provenance_snapshot(
            project=self.project, actor_membership=self.mem_dir, title="v1"
        )

        json_export = export_credits_json(snapshot)
        self.assertIn("Public Movie", json_export)
        self.assertIn("Gen Artist", json_export)

        csv_export = export_credits_csv(snapshot)
        self.assertIn("Credited Name", csv_export)
        self.assertIn("Gen Artist", csv_export)

    def test_private_project_returns_404_for_anonymous(self):
        url = reverse("public_project", kwargs={"slug": self.private_project.slug})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_hidden_contributor_profile_returns_404(self):
        url = reverse("public_contributor_profile", kwargs={"handle": "nonexistent_handle"})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)
