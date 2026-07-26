from django.test import Client, TestCase
from django.urls import reverse


class Issue1AuthUIStyleTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_navbar_login_link_points_to_standard_auth_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)  # Dashboard redirects to login if unauthenticated
        self.assertIn(reverse("login"), response.url)

    def test_registration_view_renders_scannable_form(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")
        self.assertContains(response, "Password Requirements")
        self.assertContains(response, "At least 8 characters long")
        self.assertNotContains(response, "admin/login")

    def test_login_view_renders_custom_auth_template(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In")
        self.assertContains(response, "Register for Modern Movie Crew")
