from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.characters.models import Character, CharacterIdentityVersion
from apps.production.models import PacketSection
from apps.projects.models import Department, Membership, ProductionRole, Project, RoleAssignment
from services.boundary_services import verify_department_match
from services.character_services import approve_character_identity
from services.production_services import approve_packet_section, create_production_task_with_packet

User = get_user_model()


class Issue4DirectorAuthorityTest(TestCase):
    def setUp(self):
        self.user_dir = User.objects.create_user(username="director_a", password="Password123!")
        self.user_art_head = User.objects.create_user(username="art_head", password="Password123!")
        self.user_dir_b = User.objects.create_user(username="director_b", password="Password123!")

        self.project_a = Project.objects.create(name="Project A", slug="proj-a", created_by=self.user_dir)
        self.project_b = Project.objects.create(name="Project B", slug="proj-b", created_by=self.user_dir_b)

        # Project A Departments
        self.dept_direction = Department.objects.create(project=self.project_a, name="Direction Department")
        self.dept_art = Department.objects.create(project=self.project_a, name="Art Department")
        self.dept_sound = Department.objects.create(project=self.project_a, name="Sound Department")

        # Project A Roles
        self.role_director_a = ProductionRole.objects.create(
            project=self.project_a,
            department=self.dept_direction,
            name="Director",
            can_accept_final_assets=True,
            can_approve_department_work=True,
        )
        self.role_art_head = ProductionRole.objects.create(
            project=self.project_a,
            department=self.dept_art,
            name="Art Director",
            can_accept_final_assets=False,
            can_approve_department_work=True,
        )

        # Memberships
        self.membership_dir_a = Membership.objects.create(
            project=self.project_a, user=self.user_dir, credited_name="Director A"
        )
        self.membership_art_head = Membership.objects.create(
            project=self.project_a, user=self.user_art_head, credited_name="Art Head"
        )

        # Assignments
        self.assignment_dir_a = RoleAssignment.objects.create(
            membership=self.membership_dir_a, role=self.role_director_a
        )
        self.assignment_art_head = RoleAssignment.objects.create(
            membership=self.membership_art_head, role=self.role_art_head
        )

        # Task and Packet in Art Department
        self.task_a = create_production_task_with_packet(
            project=self.project_a,
            actor_membership=self.membership_dir_a,
            code="TASK-01",
            title="Art Concept Task",
        )
        self.art_section = self.task_a.packet_sections.first()

        # Packet section in Sound Department
        self.sound_section = PacketSection.objects.create(
            task=self.task_a,
            department=self.dept_sound,
            section_type=PacketSection.SectionType.PERFORMANCE,
            content="Performance prompt",
            required=True,
        )

        # Character Identity
        self.character = Character.objects.create(project=self.project_a, name="Hero Character")
        self.identity_v1 = CharacterIdentityVersion.objects.create(
            character=self.character, version_number=1, facial_structure_notes="Strong jawline"
        )

    def test_director_cross_department_approval_success(self):
        # Director (in Direction Dept) approving Art Section
        approved_art = approve_packet_section(
            packet_section=self.art_section,
            reviewer_assignment=self.assignment_dir_a,
        )
        self.assertEqual(approved_art.status, PacketSection.Status.APPROVED)

        # Director approving Sound Section
        approved_sound = approve_packet_section(
            packet_section=self.sound_section,
            reviewer_assignment=self.assignment_dir_a,
        )
        self.assertEqual(approved_sound.status, PacketSection.Status.APPROVED)

        # Director approving Character Identity
        approved_id = approve_character_identity(
            identity_version=self.identity_v1,
            reviewer_assignment=self.assignment_dir_a,
        )
        self.assertEqual(approved_id.status, CharacterIdentityVersion.Status.APPROVED)

    def test_department_head_restricted_to_own_department(self):
        # Art Head can approve Art Section
        approved_art = approve_packet_section(
            packet_section=self.art_section,
            reviewer_assignment=self.assignment_art_head,
        )
        self.assertEqual(approved_art.status, PacketSection.Status.APPROVED)

        # Art Head CANNOT approve Sound Section
        with self.assertRaises(PermissionDenied):
            approve_packet_section(
                packet_section=self.sound_section,
                reviewer_assignment=self.assignment_art_head,
            )

    def test_director_denied_cross_project(self):
        # Project B Director
        dept_dir_b = Department.objects.create(project=self.project_b, name="Direction Dept B")
        role_dir_b = ProductionRole.objects.create(
            project=self.project_b,
            department=dept_dir_b,
            name="Director B",
            can_accept_final_assets=True,
        )
        membership_dir_b = Membership.objects.create(
            project=self.project_b, user=self.user_dir_b, credited_name="Director B"
        )
        assignment_dir_b = RoleAssignment.objects.create(
            membership=membership_dir_b, role=role_dir_b
        )

        # Director B cannot approve Project A packet section
        with self.assertRaises(PermissionDenied):
            approve_packet_section(
                packet_section=self.art_section,
                reviewer_assignment=assignment_dir_b,
            )
