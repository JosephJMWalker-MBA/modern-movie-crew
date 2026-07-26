from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.production.models import ProductionTask
from apps.projects.models import Membership, Project
from apps.submissions.models import (
    CanonicalSelection,
    Submission,
    SubmissionVersion,
)

User = get_user_model()


class SubmissionsModelBoundaryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="p")
        self.project = Project.objects.create(
            name="Proj A", slug="proj-a", created_by=self.user
        )
        self.member = Membership.objects.create(
            project=self.project, user=self.user, credited_name="User 1"
        )
        self.task = ProductionTask.objects.create(
            project=self.project, code="TASK_01", title="Task 1", task_type="video"
        )
        self.submission = Submission.objects.create(
            task=self.task, contributor=self.member
        )

    def test_submission_version_immutability(self):
        version = SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=1,
            storage_key="s3://path/v1.mp4",
            created_by=self.member,
        )
        self.assertIsNotNone(version.pk)

        # Updating an existing SubmissionVersion should fail
        version.storage_key = "s3://path/v1_modified.mp4"
        with self.assertRaises(ValidationError):
            version.save()

        # Deleting a SubmissionVersion should fail
        with self.assertRaises(ValidationError):
            version.delete()

    def test_only_one_active_canonical_selection_per_task(self):
        v1 = SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=1,
            storage_key="s3://v1.mp4",
            created_by=self.member,
        )
        v2 = SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=2,
            storage_key="s3://v2.mp4",
            created_by=self.member,
        )

        sel1 = CanonicalSelection.objects.create(
            task=self.task, submission_version=v1, selected_by=self.member
        )
        self.assertIsNone(sel1.retired_at)

        # Creating a second active canonical selection without retiring the first should raise IntegrityError
        with self.assertRaises(IntegrityError):
            CanonicalSelection.objects.create(
                task=self.task, submission_version=v2, selected_by=self.member
            )
