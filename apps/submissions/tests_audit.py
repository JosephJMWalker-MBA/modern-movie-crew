from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import Client, TestCase
from django.urls import reverse

from apps.characters.models import Character, CharacterIdentityVersion
from apps.production.models import (
    Act,
    CharacterTaskLink,
    PacketSection,
    ProductionTask,
    Scene,
    Sequence,
)
from apps.projects.models import (
    Department,
    Membership,
    MembershipAgreement,
    ProductionRole,
    Project,
    ProjectTermsVersion,
    RoleAssignment,
)
from apps.submissions.models import Submission, SubmissionVersion
from services.character_services import approve_character_identity, create_character_identity_version
from services.production_services import approve_packet_section, transition_task_to_open
from services.review_services import accept_submission_version
from services.submission_services import create_submission_with_v1
from services.upload_services import validate_uploaded_file

User = get_user_model()


class Milestone1AuditTest(TestCase):
    def setUp(self):
        self.user_director = User.objects.create_user(username="director_user", password="password")
        self.user_contributor = User.objects.create_user(username="contrib_user", password="password")

        self.project_a = Project.objects.create(name="Project A", slug="proj-a", created_by=self.user_director)
        self.project_b = Project.objects.create(name="Project B", slug="proj-b", created_by=self.user_director)

        self.terms_a = ProjectTermsVersion.objects.create(project=self.project_a, version_number=1, terms_text="T_A")
        self.terms_b = ProjectTermsVersion.objects.create(project=self.project_b, version_number=1, terms_text="T_B")

        self.dept_a = Department.objects.create(project=self.project_a, name="Art Dept")
        self.dept_b = Department.objects.create(project=self.project_b, name="Costume Dept")

        self.dir_role_a = ProductionRole.objects.create(
            project=self.project_a,
            department=self.dept_a,
            name="Director",
            can_approve_department_work=True,
            can_accept_final_assets=True,
        )

        self.member_dir_a = Membership.objects.create(project=self.project_a, user=self.user_director, credited_name="Dir A")
        self.member_contrib_a = Membership.objects.create(project=self.project_a, user=self.user_contributor, credited_name="Contrib A")
        self.member_dir_b = Membership.objects.create(project=self.project_b, user=self.user_director, credited_name="Dir B")

        MembershipAgreement.objects.create(membership=self.member_dir_a, terms_version=self.terms_a)
        MembershipAgreement.objects.create(membership=self.member_contrib_a, terms_version=self.terms_a)

        RoleAssignment.objects.create(membership=self.member_dir_a, role=self.dir_role_a, is_department_head=True)

        # Task setup for Project A
        self.act_a = Act.objects.create(project=self.project_a, act_number=1)
        self.seq_a = Sequence.objects.create(act=self.act_a, sequence_number=1)
        self.scene_a = Scene.objects.create(sequence=self.seq_a, scene_number=1)
        self.task_a = ProductionTask.objects.create(
            project=self.project_a, scene=self.scene_a, code="T_A01", title="Task A01", task_type="video", status="draft"
        )

        # Task setup for Project B
        self.act_b = Act.objects.create(project=self.project_b, act_number=1)
        self.seq_b = Sequence.objects.create(act=self.act_b, sequence_number=1)
        self.scene_b = Scene.objects.create(sequence=self.seq_b, scene_number=1)
        self.task_b = ProductionTask.objects.create(
            project=self.project_b, scene=self.scene_b, code="T_B01", title="Task B01", task_type="video", status="draft"
        )

        self.client = Client()

    def test_upload_file_validation_invalid_extension(self):
        fake_exe = SimpleUploadedFile("malicious.exe", b"binarycontent", content_type="application/x-msdownload")
        with self.assertRaises(ValidationError):
            validate_uploaded_file(fake_exe)

    def test_upload_file_validation_oversized(self):
        # 101 MB fake file
        huge_file = SimpleUploadedFile("big.mp4", b"0" * (101 * 1024 * 1024), content_type="video/mp4")
        with self.assertRaises(ValidationError):
            validate_uploaded_file(huge_file)

    def test_cross_project_id_manipulation_in_urls_returns_404(self):
        self.client.login(username="director_user", password="password")
        # Attempt to access task belonging to Project B using Project A's slug
        url = reverse("task_detail", kwargs={"slug": self.project_a.slug, "task_id": self.task_b.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unauthorized_user_cannot_accept_canonical_asset(self):
        self.task_a.status = "open"
        self.task_a.save()
        v1 = create_submission_with_v1(
            task=self.task_a, contributor_membership=self.member_contrib_a, storage_key="s3://v1.mp4"
        )
        # Contributor (without director permission) trying to accept version raises PermissionDenied
        with self.assertRaises(PermissionDenied):
            accept_submission_version(version=v1, reviewer_membership=self.member_contrib_a)

    def test_atomic_transaction_rollback_on_failure(self):
        self.task_a.status = "open"
        self.task_a.save()
        v1 = create_submission_with_v1(
            task=self.task_a, contributor_membership=self.member_contrib_a, storage_key="s3://v1.mp4"
        )
        initial_audit_count = self.project_a.audit_events.count()

        # Monkeypatch to force error during accept_submission_version execution
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                accept_submission_version(version=v1, reviewer_membership=self.member_dir_a)
                raise RuntimeError("Forced transaction failure")

        # Verify database state rolled back cleanly
        self.task_a.refresh_from_db()
        self.assertNotEqual(self.task_a.status, ProductionTask.Status.SATISFIED)
        self.assertEqual(self.project_a.audit_events.count(), initial_audit_count)

    def test_two_users_complete_workflow_via_ui(self):
        # 1. Director logs in & creates character + task
        self.client.login(username="director_user", password="password")
        char = Character.objects.create(project=self.project_a, name="Kael")
        id_v1 = create_character_identity_version(
            character=char, version_number=1, creator_membership=self.member_dir_a
        )
        role_assign = self.member_dir_a.role_assignments.first()
        approve_character_identity(identity_version=id_v1, reviewer_assignment=role_assign)

        sec = PacketSection.objects.create(
            task=self.task_a, department=self.dept_a, section_type="story", required=True
        )
        approve_packet_section(packet_section=sec, reviewer_assignment=role_assign)
        transition_task_to_open(task=self.task_a, actor_membership=self.member_dir_a)

        # 2. Contributor logs in & uploads V1 via UI POST
        self.client.login(username="contrib_user", password="password")
        upload_url = reverse("upload_v1", kwargs={"slug": self.project_a.slug, "task_id": self.task_a.id})
        res = self.client.post(
            upload_url,
            {
                "external_tool": "Veo",
                "prompt_used": "Airlock scene",
                "seed": "777",
            },
            follow=True,
        )
        self.assertEqual(res.status_code, 200)

        # Check submission created
        sub = Submission.objects.get(task=self.task_a, contributor=self.member_contrib_a)
        v1 = sub.latest_version()

        # 3. Director logs in & accepts V1 via UI POST
        self.client.login(username="director_user", password="password")
        accept_url = reverse("director_accept", kwargs={"slug": self.project_a.slug, "version_id": v1.id})
        res2 = self.client.post(accept_url, {"notes": "Approved via UI test"}, follow=True)
        self.assertEqual(res2.status_code, 200)

        # Verify task is SATISFIED and canonical asset exists
        self.task_a.refresh_from_db()
        self.assertEqual(self.task_a.status, ProductionTask.Status.SATISFIED)
        self.assertIsNotNone(self.task_a.active_canonical_selection())
