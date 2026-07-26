from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.projects.models import (
    Department,
    Membership,
    MembershipAgreement,
    ProductionRole,
    Project,
    ProjectTermsVersion,
    RoleAssignment,
)

User = get_user_model()


class ProjectsModelBoundaryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="password")
        self.project_a = Project.objects.create(
            name="Project A", slug="project-a", created_by=self.user
        )
        self.project_b = Project.objects.create(
            name="Project B", slug="project-b", created_by=self.user
        )

        self.dept_a = Department.objects.create(
            project=self.project_a, name="Art Dept"
        )
        self.dept_b = Department.objects.create(
            project=self.project_b, name="Costume Dept"
        )

        self.member_a = Membership.objects.create(
            project=self.project_a, user=self.user, credited_name="User A"
        )
        self.member_b = Membership.objects.create(
            project=self.project_b, user=self.user, credited_name="User B"
        )

        self.role_a = ProductionRole.objects.create(
            project=self.project_a, department=self.dept_a, name="Art Lead"
        )

    def test_membership_agreement_cross_project_rejection(self):
        terms_b = ProjectTermsVersion.objects.create(
            project=self.project_b, version_number=1, terms_text="Terms B"
        )
        agreement = MembershipAgreement(
            membership=self.member_a, terms_version=terms_b
        )
        with self.assertRaises(ValidationError):
            agreement.save()

    def test_production_role_cross_department_rejection(self):
        role_invalid = ProductionRole(
            project=self.project_a, department=self.dept_b, name="Invalid Role"
        )
        with self.assertRaises(ValidationError):
            role_invalid.save()

    def test_role_assignment_cross_project_rejection(self):
        assignment = RoleAssignment(membership=self.member_b, role=self.role_a)
        with self.assertRaises(ValidationError):
            assignment.save()
