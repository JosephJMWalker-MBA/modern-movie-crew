from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.projects.models import Membership, ProductionRole, Project
from services.project_services import create_project_with_defaults

User = get_user_model()


class Issue2InviteRolesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_director = User.objects.create_user(username="director_user", password="Password123!")
        self.project = create_project_with_defaults(
            creator_user=self.user_director,
            name="Invite Test Project",
            synopsis="Testing invite roles",
        )
        self.client.force_login(self.user_director)

    def test_default_safe_roles_created_on_project_creation(self):
        safe_roles = [r for r in self.project.roles.all() if r.is_safe_invite_role()]
        self.assertGreater(len(safe_roles), 0)
        safe_role_names = [r.name for r in safe_roles]
        self.assertIn("Generation Contributor", safe_role_names)

    def test_create_invite_view_lists_only_safe_roles(self):
        response = self.client.get(reverse("create_invite", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        roles_in_context = response.context["roles"]
        for role in roles_in_context:
            self.assertTrue(role.is_safe_invite_role())
            self.assertFalse(role.can_accept_final_assets)
            self.assertFalse(role.can_manage_credits)

    def test_empty_state_and_seed_roles_action(self):
        # Remove all safe roles
        for role in self.project.roles.all():
            if role.is_safe_invite_role():
                role.delete()

        response = self.client.get(reverse("create_invite", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["roles"]), 0)
        self.assertContains(response, "No Safe Contributor Roles Available")

        # Post seed_roles action
        post_response = self.client.post(
            reverse("create_invite", kwargs={"slug": self.project.slug}),
            {"action": "seed_roles"},
            follow=True,
        )
        self.assertEqual(post_response.status_code, 200)
        safe_roles_after = [r for r in self.project.roles.all() if r.is_safe_invite_role()]
        self.assertGreater(len(safe_roles_after), 0)
