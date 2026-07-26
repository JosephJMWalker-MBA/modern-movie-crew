from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AuditEvent
from apps.projects.models import Membership, Project

User = get_user_model()


class AuditEventModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.project = Project.objects.create(
            name="Test Film", slug="test-film", created_by=self.user
        )
        self.membership = Membership.objects.create(
            project=self.project, user=self.user, credited_name="Test User"
        )

    def test_audit_event_is_append_only(self):
        event = AuditEvent.objects.create(
            project=self.project,
            actor=self.membership,
            event_type="test_event",
            object_type="project",
            object_id=str(self.project.id),
        )
        self.assertIsNotNone(event.pk)

        # Attempt to modify should raise RuntimeError
        event.event_type = "modified_event"
        with self.assertRaises(RuntimeError):
            event.save()

        # Attempt to delete should raise RuntimeError
        with self.assertRaises(RuntimeError):
            event.delete()
