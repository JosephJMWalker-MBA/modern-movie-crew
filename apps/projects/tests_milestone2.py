from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Notification
from apps.production.models import Act, ProductionTask, Scene, Sequence
from apps.projects.models import (
    Department,
    Membership,
    ProductionRole,
    Project,
    ProjectInviteToken,
    ProjectTermsVersion,
)
from services.invite_services import (
    accept_project_invite,
    create_project_invite,
    revoke_project_invite,
)
from services.matching_services import find_eligible_open_tasks_for_contributor
from services.production_services import claim_production_task

User = get_user_model()


class Milestone2CommunityRoomTest(TestCase):
    def setUp(self):
        self.user_director = User.objects.create_user(username="director_m2", password="password")
        self.user_contributor = User.objects.create_user(username="contrib_m2", password="password")
        self.user_newbie = User.objects.create_user(username="newbie_m2", password="password")

        self.project_a = Project.objects.create(name="Project A", slug="proj-m2-a", created_by=self.user_director)
        self.project_b = Project.objects.create(name="Project B", slug="proj-m2-b", created_by=self.user_director)

        self.terms_a = ProjectTermsVersion.objects.create(project=self.project_a, version_number=1, terms_text="Terms A")
        self.terms_b = ProjectTermsVersion.objects.create(project=self.project_b, version_number=1, terms_text="Terms B")

        self.dept_a = Department.objects.create(project=self.project_a, name="Art Department")
        self.dept_b = Department.objects.create(project=self.project_b, name="Costume Department")

        # Roles
        self.dir_role_a = ProductionRole.objects.create(
            project=self.project_a, department=self.dept_a, name="Director", can_accept_final_assets=True, can_manage_credits=True
        )

        self.gen_role_a = ProductionRole.objects.create(
            project=self.project_a, department=self.dept_a, name="Prompt Specialist"
        )

        self.gen_role_b = ProductionRole.objects.create(
            project=self.project_b, department=self.dept_b, name="Costume Assistant"
        )

        self.mem_dir_a = Membership.objects.create(project=self.project_a, user=self.user_director, credited_name="Director A")
        self.mem_dir_a.role_assignments.create(role=self.dir_role_a, is_department_head=True)

        self.mem_contrib_a = Membership.objects.create(project=self.project_a, user=self.user_contributor, credited_name="Contributor A")
        self.mem_contrib_a.role_assignments.create(role=self.gen_role_a)

    def test_permission_escalation_prevention_on_invite_tokens(self):
        # Attempting to create an invite token with director asset-acceptance authority must fail
        with self.assertRaises(ValidationError):
            create_project_invite(
                project=self.project_a,
                actor_membership=self.mem_dir_a,
                default_role=self.dir_role_a,
            )

    def test_create_and_accept_valid_invite(self):
        invite = create_project_invite(
            project=self.project_a,
            actor_membership=self.mem_dir_a,
            default_role=self.gen_role_a,
            max_uses=2,
        )

        # Accept invite as newbie user
        new_mem = accept_project_invite(
            token_str=invite.token, user=self.user_newbie, credited_name="Newbie Artist"
        )

        self.assertEqual(new_mem.project, self.project_a)
        self.assertEqual(new_mem.user, self.user_newbie)
        self.assertTrue(new_mem.agreements.filter(terms_version=self.terms_a).exists())

        # Check notification sent to invite creator
        self.assertTrue(
            Notification.objects.filter(
                membership=self.mem_dir_a, title="Invite Accepted"
            ).exists()
        )

    def test_revoked_or_expired_invite_acceptance_fails(self):
        invite = create_project_invite(
            project=self.project_a,
            actor_membership=self.mem_dir_a,
            default_role=self.gen_role_a,
        )

        # Revoke invite
        revoke_project_invite(invite_token=invite, actor_membership=self.mem_dir_a)

        # Attempting to accept revoked invite must fail
        with self.assertRaises(ValidationError):
            accept_project_invite(token_str=invite.token, user=self.user_newbie)

    def test_duplicate_invite_acceptance_fails(self):
        invite = create_project_invite(
            project=self.project_a,
            actor_membership=self.mem_dir_a,
            default_role=self.gen_role_a,
        )

        # Attempting to accept invite when user is already a member must fail
        with self.assertRaises(ValidationError):
            accept_project_invite(token_str=invite.token, user=self.user_contributor)

    def test_spare_gen_task_matching_non_mutating(self):
        act = Act.objects.create(project=self.project_a, act_number=1)
        seq = Sequence.objects.create(act=act, sequence_number=1)
        scene = Scene.objects.create(sequence=seq, scene_number=1)

        task1 = ProductionTask.objects.create(
            project=self.project_a, scene=scene, code="V01", title="Video Shot", task_type="video", status="open"
        )
        task2 = ProductionTask.objects.create(
            project=self.project_a, scene=scene, code="S01", title="Voice Track", task_type="voice", status="open"
        )

        # Query matching tasks for video asset type
        matches = find_eligible_open_tasks_for_contributor(
            membership=self.mem_contrib_a, asset_types=["video"]
        )

        self.assertIn(task1, matches)
        self.assertNotIn(task2, matches)

        # Verify query DID NOT mutate task state!
        task1.refresh_from_db()
        self.assertEqual(task1.status, ProductionTask.Status.OPEN)
        self.assertEqual(task1.claims.count(), 0)

    def test_transactional_notification_on_task_claim(self):
        act = Act.objects.create(project=self.project_a, act_number=1)
        seq = Sequence.objects.create(act=act, sequence_number=1)
        scene = Scene.objects.create(sequence=seq, scene_number=1)
        task = ProductionTask.objects.create(
            project=self.project_a, scene=scene, code="C01", title="Claimable", task_type="video", status="open"
        )

        claim_production_task(task=task, contributor_membership=self.mem_contrib_a)

        # Verify notification created for project director
        notif = Notification.objects.filter(membership=self.mem_dir_a, title="Task Claimed").first()
        self.assertIsNotNone(notif)
        self.assertIn("claimed task C01", notif.message)
