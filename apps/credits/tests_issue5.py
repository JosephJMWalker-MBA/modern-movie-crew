from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.credits.models import CreditEntry
from apps.projects.models import Department, Membership, ProductionRole, Project

User = get_user_model()


class CreditLedgerIssue5Test(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_member = User.objects.create_user(username="member_user", password="Password123!")
        self.user_non_member = User.objects.create_user(username="other_user", password="Password123!")

        self.project_a = Project.objects.create(name="Project A", slug="proj-a")
        self.project_b = Project.objects.create(name="Project B", slug="proj-b")

        self.dept_art = Department.objects.create(project=self.project_a, name="Art Department")
        self.role_dir = ProductionRole.objects.create(
            department=self.dept_art,
            name="Director",
            can_accept_final_assets=True,
        )

        self.membership_a = Membership.objects.create(
            project=self.project_a,
            user=self.user_member,
            credited_name="Director Member",
        )

    def test_credit_ledger_empty(self):
        self.client.force_login(self.user_member)
        response = self.client.get(reverse("credit_ledger", kwargs={"slug": "proj-a"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project A")
        self.assertEqual(len(response.context["credits_list"]), 0)

    def test_credit_ledger_with_various_credit_bases(self):
        # Create credit entries with different bases
        CreditEntry.objects.create(
            project=self.project_a,
            contributor=self.membership_a,
            credited_name="Director Member",
            role_name="Director",
            department_name="Art Department",
            basis=CreditEntry.Basis.ROLE,
        )
        CreditEntry.objects.create(
            project=self.project_a,
            contributor=self.membership_a,
            credited_name="Director Member",
            role_name="Director",
            department_name="Art Department",
            basis=CreditEntry.Basis.RESPONSIBILITY,
        )
        CreditEntry.objects.create(
            project=self.project_a,
            contributor=self.membership_a,
            credited_name="Director Member",
            role_name="Director",
            department_name="Art Department",
            basis=CreditEntry.Basis.ACCEPTED_WORK,
            is_final_cut=True,
        )

        self.client.force_login(self.user_member)
        response = self.client.get(reverse("credit_ledger", kwargs={"slug": "proj-a"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["credits_list"]), 3)

    def test_credit_ledger_non_member_isolation(self):
        self.client.force_login(self.user_non_member)
        response = self.client.get(reverse("credit_ledger", kwargs={"slug": "proj-a"}))
        self.assertEqual(response.status_code, 404)

    def test_credit_ledger_cross_project_isolation(self):
        # Credit in project B
        membership_b = Membership.objects.create(
            project=self.project_b,
            user=self.user_non_member,
            credited_name="Other Member",
        )
        CreditEntry.objects.create(
            project=self.project_b,
            contributor=membership_b,
            credited_name="Other Member",
            role_name="Editor",
            department_name="Editorial",
            basis=CreditEntry.Basis.ROLE,
        )

        self.client.force_login(self.user_member)
        response = self.client.get(reverse("credit_ledger", kwargs={"slug": "proj-a"}))
        self.assertEqual(response.status_code, 200)
        # Project B credit must not appear on Project A ledger
        for credit in response.context["credits_list"]:
            self.assertEqual(credit.project, self.project_a)
