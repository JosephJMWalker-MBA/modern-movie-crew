from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.credits.models import CreditEntry
from apps.projects.models import Membership, Project

User = get_user_model()


class CreditsModelBoundaryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="p")
        self.proj_a = Project.objects.create(
            name="Proj A", slug="proj-a", created_by=self.user
        )
        self.proj_b = Project.objects.create(
            name="Proj B", slug="proj-b", created_by=self.user
        )

        self.member_a = Membership.objects.create(
            project=self.proj_a, user=self.user, credited_name="User A"
        )
        self.member_b = Membership.objects.create(
            project=self.proj_b, user=self.user, credited_name="User B"
        )

    def test_credit_entry_cross_project_rejection(self):
        credit = CreditEntry(
            project=self.proj_a,
            contributor=self.member_b,
            credited_name="User B",
            role_name="Editor",
            department_name="Post",
            basis="role",
        )
        with self.assertRaises(ValidationError):
            credit.save()

    def test_credit_entry_historical_snapshot_immutability(self):
        credit = CreditEntry.objects.create(
            project=self.proj_a,
            contributor=self.member_a,
            credited_name="Original Name",
            role_name="Costume Designer",
            department_name="Costume Dept",
            basis="responsibility",
        )
        self.assertIsNotNone(credit.pk)

        # Altering snapshot name must raise ValidationError
        credit.credited_name = "New Profile Name"
        with self.assertRaises(ValidationError):
            credit.save()
