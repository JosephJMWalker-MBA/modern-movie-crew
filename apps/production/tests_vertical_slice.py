from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.characters.models import Character, CharacterIdentityVersion
from apps.credits.models import CreditEntry
from apps.production.models import (
    Act,
    CharacterTaskLink,
    PacketSection,
    ProductionTask,
    Scene,
    Sequence,
    TaskClaim,
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
from apps.submissions.models import (
    CanonicalSelection,
    DirectorReview,
    Submission,
    SubmissionVersion,
)
from services.character_services import (
    approve_character_identity,
    create_character_identity_version,
)
from services.production_services import (
    approve_packet_section,
    claim_production_task,
    transition_task_to_open,
)
from services.review_services import accept_submission_version
from services.submission_services import (
    create_submission_v2,
    create_submission_with_v1,
    request_submission_revision,
    submit_department_review,
)

User = get_user_model()


class EndToEndVerticalSliceTest(TestCase):
    def setUp(self):
        # 1. Create Users & Project
        self.director_user = User.objects.create_user(username="director", password="password")
        self.artist_user = User.objects.create_user(username="artist", password="password")
        self.contributor_user = User.objects.create_user(username="contributor", password="password")

        self.project = Project.objects.create(
            name="Lunar Airlock 14", slug="lunar-airlock-14", created_by=self.director_user
        )

        self.terms = ProjectTermsVersion.objects.create(
            project=self.project, version_number=1, terms_text="Project Terms v1"
        )

        # 2. Departments & Roles
        self.art_dept = Department.objects.create(project=self.project, name="Art Department", sort_order=1)
        self.gen_dept = Department.objects.create(project=self.project, name="Generation Department", sort_order=2)
        self.dir_dept = Department.objects.create(project=self.project, name="Direction Department", sort_order=0)

        self.director_role = ProductionRole.objects.create(
            project=self.project,
            department=self.dir_dept,
            name="Director",
            can_assign_tasks=True,
            can_approve_department_work=True,
            can_accept_final_assets=True,
            can_manage_credits=True,
        )

        self.art_lead_role = ProductionRole.objects.create(
            project=self.project,
            department=self.art_dept,
            name="Art Lead",
            can_approve_department_work=True,
        )

        self.generator_role = ProductionRole.objects.create(
            project=self.project,
            department=self.gen_dept,
            name="Prompt Specialist",
        )

        # Memberships
        self.director_mem = Membership.objects.create(
            project=self.project, user=self.director_user, credited_name="Director Director"
        )
        self.artist_mem = Membership.objects.create(
            project=self.project, user=self.artist_user, credited_name="Art Lead Designer"
        )
        self.contributor_mem = Membership.objects.create(
            project=self.project, user=self.contributor_user, credited_name="Gen Contributor"
        )

        # Terms Acceptance
        MembershipAgreement.objects.create(membership=self.director_mem, terms_version=self.terms)
        MembershipAgreement.objects.create(membership=self.artist_mem, terms_version=self.terms)
        MembershipAgreement.objects.create(membership=self.contributor_mem, terms_version=self.terms)

        # Role Assignments
        self.director_assign = RoleAssignment.objects.create(
            membership=self.director_mem, role=self.director_role, is_department_head=True
        )
        self.artist_assign = RoleAssignment.objects.create(
            membership=self.artist_mem, role=self.art_lead_role, is_department_head=True
        )
        self.contributor_assign = RoleAssignment.objects.create(
            membership=self.contributor_mem, role=self.generator_role
        )

    def test_full_governed_production_vertical_slice(self):
        # Step 1: Create Act -> Sequence -> Scene structure
        act = Act.objects.create(project=self.project, act_number=1, title="Act I: Arrival")
        seq = Sequence.objects.create(act=act, sequence_number=1, title="Sequence A")
        scene = Scene.objects.create(sequence=seq, scene_number=14, title="Lunar Airlock Arrival")

        # Step 2: Create & Approve Character Identity
        character = Character.objects.create(project=self.project, name="Imani")
        identity_v1 = create_character_identity_version(
            character=character,
            version_number=1,
            facial_structure_notes="High cheekbones, dark eyes, retrofuturist helmet",
            creator_membership=self.artist_mem,
        )
        approve_character_identity(
            identity_version=identity_v1, reviewer_assignment=self.artist_assign
        )
        self.assertEqual(identity_v1.status, CharacterIdentityVersion.Status.APPROVED)

        # Step 3: Create Task & Link Character
        task = ProductionTask.objects.create(
            project=self.project,
            scene=scene,
            code="SC14_SH03",
            title="Exterior Airlock Establishing Shot",
            task_type="video",
        )

        link = CharacterTaskLink.objects.create(
            task=task, character=character, character_identity_version=identity_v1
        )

        # Step 4: Create & Approve Required Packet Sections
        packet_sec = PacketSection.objects.create(
            task=task,
            department=self.art_dept,
            section_type=PacketSection.SectionType.STORY,
            content="8-12 second wide establishing shot of rover approaching airlock",
            required=True,
        )
        approve_packet_section(packet_section=packet_sec, reviewer_assignment=self.artist_assign)
        self.assertEqual(packet_sec.status, PacketSection.Status.APPROVED)

        # Step 5: Transition Task to OPEN
        transition_task_to_open(task=task, actor_membership=self.director_mem)
        self.assertEqual(task.status, ProductionTask.Status.OPEN)

        # Step 6: Contributor Claims Task
        claim = claim_production_task(task=task, contributor_membership=self.contributor_mem)
        self.assertEqual(claim.status, TaskClaim.Status.ACTIVE)

        # Step 7: Upload Submission V1 with Rights Attestation
        v1 = create_submission_with_v1(
            task=task,
            contributor_membership=self.contributor_mem,
            storage_key="s3://lunar-bucket/SC14_SH03_v1.mp4",
            external_tool="Sora",
            prompt_used="Cinematic retrofuturist lunar airlock exterior establishing shot",
            seed="101010",
        )
        submission = v1.submission
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(submission.status, Submission.Status.IN_REVIEW)
        self.assertTrue(hasattr(v1, "attestation"))

        # Step 8: Department Review (Issue Found / Revision Recommended)
        dept_rev = submit_department_review(
            version=v1,
            reviewer_assignment=self.artist_assign,
            decision="revision_recommended",
            notes="Airlock helmet color must be colder blue per sequence rules.",
        )
        self.assertEqual(dept_rev.decision, "revision_recommended")

        # Step 9: Director Requests Revision (Task remains OPEN!)
        dir_rev = request_submission_revision(
            version=v1,
            reviewer_membership=self.director_mem,
            notes="Please fix helmet color to match cold blue sequence rules for Take 2.",
        )
        submission.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(dir_rev.decision, DirectorReview.Decision.REQUEST_REVISION)
        self.assertEqual(submission.status, Submission.Status.REVISION_REQUESTED)
        self.assertEqual(task.status, ProductionTask.Status.OPEN)  # Task MUST remain OPEN!

        # Step 10: Contributor Uploads Immutable Submission V2
        v2 = create_submission_v2(
            submission=submission,
            contributor_membership=self.contributor_mem,
            storage_key="s3://lunar-bucket/SC14_SH03_v2.mp4",
            external_tool="Sora v2",
            prompt_used="Cold blue cinematic retrofuturist lunar airlock exterior shot",
            seed="202020",
        )
        submission.refresh_from_db()
        self.assertEqual(v2.version_number, 2)
        self.assertEqual(submission.status, Submission.Status.IN_REVIEW)

        # Attempting to edit V2 must fail due to immutability rules
        v2.prompt_used = "Illegal prompt edit"
        with self.assertRaises(Exception):
            v2.save()

        # Step 11: Director Accepts V2
        accept_rev = accept_submission_version(
            version=v2,
            reviewer_membership=self.director_mem,
            notes="Accepted as canonical establishing shot.",
        )
        submission.refresh_from_db()
        task.refresh_from_db()

        self.assertEqual(accept_rev.decision, DirectorReview.Decision.ACCEPT)
        self.assertEqual(submission.status, Submission.Status.ACCEPTED)
        self.assertEqual(task.status, ProductionTask.Status.SATISFIED)

        # Step 12: Verify Active CanonicalSelection Created Atomically
        canonical = task.active_canonical_selection()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical.submission_version, v2)
        self.assertEqual(canonical.selected_by, self.director_mem)
        self.assertIsNone(canonical.retired_at)

        # Step 13: Verify Structured Credit Ledger Entries
        credits = CreditEntry.objects.filter(project=self.project)
        self.assertTrue(credits.filter(basis=CreditEntry.Basis.ACCEPTED_WORK).exists())
        self.assertTrue(credits.filter(basis=CreditEntry.Basis.RESPONSIBILITY).exists())

        accepted_credit = credits.get(basis=CreditEntry.Basis.ACCEPTED_WORK)
        self.assertEqual(accepted_credit.contributor, self.contributor_mem)
        self.assertEqual(accepted_credit.submission_version, v2)

        # Step 14: Verify Audit Events Recorded Append-Only
        audit_events = self.project.audit_events.all()
        event_types = set(audit_events.values_list("event_type", flat=True))
        self.assertIn("character_identity_approved", event_types)
        self.assertIn("packet_section_approved", event_types)
        self.assertIn("task_opened", event_types)
        self.assertIn("task_claimed", event_types)
        self.assertIn("submission_v1_created", event_types)
        self.assertIn("department_review_submitted", event_types)
        self.assertIn("submission_revision_requested", event_types)
        self.assertIn("submission_version_created", event_types)
        self.assertIn("submission_version_accepted", event_types)
