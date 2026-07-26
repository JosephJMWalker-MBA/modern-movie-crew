from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from services.publication_services import sanitize_csv_cell

User = get_user_model()


class Milestone4HardeningTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_endpoint(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "database": "connected"})

    def test_custom_404_view(self):
        response = self.client.get("/nonexistent-page-slug-404/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "404", status_code=404)

    def test_csv_formula_injection_sanitization(self):
        # Formula strings starting with =, +, -, @, \t, \r must be prepended with '
        self.assertEqual(sanitize_csv_cell("=1+2"), "'=1+2")
        self.assertEqual(sanitize_csv_cell("+CMD()"), "'+CMD()")
        self.assertEqual(sanitize_csv_cell("-100"), "'-100")
        self.assertEqual(sanitize_csv_cell("@SUM(1,2)"), "'@SUM(1,2)")
        self.assertEqual(sanitize_csv_cell("Normal Text"), "Normal Text")

    def test_open_redirect_protection_on_registration(self):
        # Malicious external redirect attempt in next parameter must be safely ignored
        response = self.client.post(
            f"{reverse('register')}?next=http://malicious-site.com/steal",
            {"username": "newuser", "password1": "password123", "password2": "password123"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        # Verify redirected to dashboard rather than malicious site
        self.assertRedirects(response, reverse("dashboard"))
