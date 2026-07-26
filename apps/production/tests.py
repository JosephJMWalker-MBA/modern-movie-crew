from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.characters.models import (
    Character,
    CharacterIdentityVersion,
    CharacterLook,
)
from apps.production.models import (
    Act,
    CharacterTaskLink,
    PacketSection,
    ProductionTask,
    Scene,
    Sequence,
)
from apps.projects.models import Department, Membership, Project

User = get_user_model()


class ProductionModelBoundaryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="p")
        self.proj_a = Project.objects.create(
            name="Proj A", slug="proj-a", created_by=self.user
        )
        self.proj_b = Project.objects.create(
            name="Proj B", slug="proj-b", created_by=self.user
        )

        self.dept_a = Department.objects.create(
            project=self.proj_a, name="Art Dept"
        )
        self.act_a = Act.objects.create(project=self.proj_a, act_number=1)
        self.seq_a = Sequence.objects.create(act=self.act_a, sequence_number=1)
        self.scene_a = Scene.objects.create(sequence=self.seq_a, scene_number=1)

        self.task_a = ProductionTask.objects.create(
            project=self.proj_a,
            scene=self.scene_a,
            code="SC01_SH01",
            title="Shot 1",
            task_type="video",
        )

        self.char_a = Character.objects.create(project=self.proj_a, name="Imani")
        self.char_b = Character.objects.create(project=self.proj_b, name="Kael")

        self.id_v1_draft = CharacterIdentityVersion.objects.create(
            character=self.char_a, version_number=1, status="draft"
        )
        self.id_v1_appr = CharacterIdentityVersion.objects.create(
            character=self.char_a, version_number=2, status="approved"
        )

    def test_character_task_link_cross_project_rejection(self):
        id_b = CharacterIdentityVersion.objects.create(
            character=self.char_b, version_number=1, status="approved"
        )
        link = CharacterTaskLink(
            task=self.task_a,
            character=self.char_b,
            character_identity_version=id_b,
        )
        with self.assertRaises(ValidationError):
            link.save()

    def test_character_task_link_mismatched_identity_version_rejection(self):
        char_a2 = Character.objects.create(project=self.proj_a, name="Aria")
        id_a2 = CharacterIdentityVersion.objects.create(
            character=char_a2, version_number=1, status="approved"
        )
        # Linking char_a but passing identity version from char_a2
        link = CharacterTaskLink(
            task=self.task_a,
            character=self.char_a,
            character_identity_version=id_a2,
        )
        with self.assertRaises(ValidationError):
            link.save()

    def test_task_cannot_open_without_approved_packet_sections(self):
        section = PacketSection.objects.create(
            task=self.task_a,
            department=self.dept_a,
            section_type="story",
            required=True,
            status="draft",
        )
        self.task_a.status = ProductionTask.Status.OPEN
        with self.assertRaises(ValidationError):
            self.task_a.save()

    def test_task_cannot_open_with_unapproved_character_identity(self):
        link = CharacterTaskLink.objects.create(
            task=self.task_a,
            character=self.char_a,
            character_identity_version=self.id_v1_draft,
        )
        self.task_a.status = ProductionTask.Status.OPEN
        with self.assertRaises(ValidationError):
            self.task_a.save()

    def test_task_opens_when_packet_and_character_identity_are_approved(self):
        section = PacketSection.objects.create(
            task=self.task_a,
            department=self.dept_a,
            section_type="story",
            required=True,
            status="approved",
        )
        link = CharacterTaskLink.objects.create(
            task=self.task_a,
            character=self.char_a,
            character_identity_version=self.id_v1_appr,
        )
        self.task_a.status = ProductionTask.Status.OPEN
        self.task_a.save()
        self.assertEqual(self.task_a.status, ProductionTask.Status.OPEN)
