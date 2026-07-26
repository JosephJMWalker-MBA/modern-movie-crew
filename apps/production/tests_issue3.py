from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.production.models import ProductionTask, ScriptDocument, ScriptSegment, ScriptVersion, TaskScriptLink
from apps.projects.models import Membership, Project
from services.project_services import create_project_with_defaults
from services.script_services import create_task_from_script_selection, import_script_document

User = get_user_model()


class Issue3ScriptWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_dir = User.objects.create_user(username="script_dir", password="Password123!")
        self.user_other = User.objects.create_user(username="other_user", password="Password123!")

        self.project_a = create_project_with_defaults(
            creator_user=self.user_dir, name="Script Movie A", synopsis="Project A"
        )
        self.project_b = create_project_with_defaults(
            creator_user=self.user_other, name="Script Movie B", synopsis="Project B"
        )

        self.membership_a = self.project_a.memberships.get(user=self.user_dir)
        self.membership_b = self.project_b.memberships.get(user=self.user_other)

        self.sample_script_text = (
            "INT. CONTROL ROOM - NIGHT\n"
            "An emergency alarm blares across dark monitors.\n"
            "COMMANDER\n"
            "Initiate neural override immediately!\n"
            "EXT. LAUNCH PAD - CONTINUOUS\n"
            "Heavy rain falls on the launch shuttle."
        )

    def test_import_script_document_parses_segments_and_scenes(self):
        version = import_script_document(
            project=self.project_a,
            title="Master Script v1",
            raw_text=self.sample_script_text,
            creator_membership=self.membership_a,
        )

        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.script_document.title, "Master Script v1")

        segments = list(version.segments.order_by("segment_number"))
        self.assertEqual(len(segments), 5)

        # Segment 1: Scene Heading
        self.assertEqual(segments[0].segment_type, ScriptSegment.SegmentType.SCENE_HEADING)
        self.assertIn("INT. CONTROL ROOM", segments[0].text_content)

        # Segment 2: Action
        self.assertEqual(segments[1].segment_type, ScriptSegment.SegmentType.ACTION)
        self.assertIn("emergency alarm", segments[1].text_content)

        # Segment 3: Dialogue
        self.assertEqual(segments[2].segment_type, ScriptSegment.SegmentType.DIALOGUE)
        self.assertIn("COMMANDER", segments[2].text_content)

        # Segment 4: Scene Heading #2
        self.assertEqual(segments[3].segment_type, ScriptSegment.SegmentType.SCENE_HEADING)
        self.assertIn("EXT. LAUNCH PAD", segments[3].text_content)

    def test_create_task_from_script_selection_traceability(self):
        version = import_script_document(
            project=self.project_a,
            title="Master Script v1",
            raw_text=self.sample_script_text,
            creator_membership=self.membership_a,
        )

        segments = list(version.segments.order_by("segment_number"))
        seg1 = segments[0]
        seg3 = segments[2]

        task1 = create_task_from_script_selection(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=version,
            start_segment=seg1,
            end_segment=seg3,
            code="TASK-SCRIPT-01",
            title="Control Room Sequence Task",
            task_type="video",
        )

        self.assertEqual(task1.code, "TASK-SCRIPT-01")
        link = task1.script_links.first()
        self.assertIsNotNone(link)
        self.assertEqual(link.script_version, version)
        self.assertEqual(link.start_segment, seg1)
        self.assertEqual(link.end_segment, seg3)
        self.assertFalse(link.has_text_drifted())

    def test_multiple_tasks_from_same_script_segment(self):
        version = import_script_document(
            project=self.project_a,
            title="Master Script v1",
            raw_text=self.sample_script_text,
            creator_membership=self.membership_a,
        )

        seg3 = version.segments.get(segment_number=3)

        # Task A: Voice
        task_voice = create_task_from_script_selection(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=version,
            start_segment=seg3,
            end_segment=seg3,
            code="TASK-VOICE-01",
            title="Commander Dialogue Voice Generation",
            task_type="voice",
        )

        # Task B: Video
        task_video = create_task_from_script_selection(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=version,
            start_segment=seg3,
            end_segment=seg3,
            code="TASK-VIDEO-01",
            title="Commander Video Shot",
            task_type="video",
        )

        self.assertEqual(task_voice.script_links.first().start_segment, seg3)
        self.assertEqual(task_video.script_links.first().start_segment, seg3)

    def test_cross_project_script_isolation_denied(self):
        version_a = import_script_document(
            project=self.project_a,
            title="Script A",
            raw_text=self.sample_script_text,
            creator_membership=self.membership_a,
        )

        seg1_a = version_a.segments.first()

        # Attempt to create task in Project B using Script A
        with self.assertRaises(ValidationError):
            create_task_from_script_selection(
                project=self.project_b,
                actor_membership=self.membership_b,
                script_version=version_a,
                start_segment=seg1_a,
                end_segment=seg1_a,
                code="TASK-PROJECT-B",
                title="Cross project task",
            )

    def test_script_workspace_and_import_views(self):
        self.client.force_login(self.user_dir)

        # Get import page
        resp_import_get = self.client.get(reverse("script_import", kwargs={"slug": self.project_a.slug}))
        self.assertEqual(resp_import_get.status_code, 200)

        # Post script import
        resp_import_post = self.client.post(
            reverse("script_import", kwargs={"slug": self.project_a.slug}),
            {"title": "Pasted Script", "raw_text": self.sample_script_text},
            follow=True,
        )
        self.assertEqual(resp_import_post.status_code, 200)

        # Get workspace view
        resp_workspace = self.client.get(reverse("script_workspace", kwargs={"slug": self.project_a.slug}))
        self.assertEqual(resp_workspace.status_code, 200)
        self.assertContains(resp_workspace, "INT. CONTROL ROOM")
        self.assertContains(resp_workspace, "Pasted Script")
