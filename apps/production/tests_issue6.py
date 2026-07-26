from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.characters.models import Character
from apps.production.models import (
    ProductionTask,
    ScriptCharacterMention,
    ScriptCharacterSuggestion,
    ScriptSegment,
    ScriptVersion,
)
from apps.projects.models import Department, Project
from services.character_discovery_services import (
    analyze_script_for_character_suggestions,
    confirm_character_suggestion,
    merge_character_alias,
    reject_character_suggestion,
)
from services.production_matrix_services import get_production_planning_matrix
from services.production_services import create_production_task_with_packet
from services.project_services import create_project_with_defaults
from services.script_services import create_task_from_script_selection, import_script_document

User = get_user_model()


class Issue6CharacterDiscoveryAndMatrixTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_dir = User.objects.create_user(username="issue6_dir", password="Password123!")
        self.user_other = User.objects.create_user(username="issue6_other", password="Password123!")

        self.project_a = create_project_with_defaults(
            creator_user=self.user_dir, name="Issue 6 Film A", synopsis="Project A"
        )
        self.project_b = create_project_with_defaults(
            creator_user=self.user_other, name="Issue 6 Film B", synopsis="Project B"
        )

        self.membership_a = self.project_a.memberships.get(user=self.user_dir)
        self.membership_b = self.project_b.memberships.get(user=self.user_other)

        self.script_text = (
            "INT. CONTROL ROOM - NIGHT\n"
            "COMMANDER (V.O.)\n"
            "Initiate neural link.\n"
            "AGENT SMITH\n"
            "Understood, Commander.\n"
            "EXT. LAUNCH PAD - DAY\n"
            "COMMANDER\n"
            "All systems green."
        )

    def test_character_extraction_from_script(self):
        version = import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )

        suggestions = ScriptCharacterSuggestion.objects.filter(script_version=version)
        names = set(s.name for s in suggestions)

        self.assertIn("COMMANDER", names)
        self.assertIn("AGENT SMITH", names)

        commander_sug = suggestions.get(name="COMMANDER")
        self.assertEqual(commander_sug.occurrence_count, 2)
        self.assertEqual(commander_sug.status, ScriptCharacterSuggestion.Status.SUGGESTED)

        # Source traceability check
        mentions = commander_sug.mentions.all()
        self.assertEqual(mentions.count(), 2)
        self.assertTrue(all(m.segment.script_version == version for m in mentions))

    def test_confirm_character_suggestion_creates_canonical_character(self):
        version = import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )
        commander_sug = version.character_suggestions.get(name="COMMANDER")

        char = confirm_character_suggestion(
            suggestion=commander_sug,
            actor_membership=self.membership_a,
        )

        self.assertIsInstance(char, Character)
        self.assertEqual(char.name, "COMMANDER")
        self.assertEqual(commander_sug.status, ScriptCharacterSuggestion.Status.CONFIRMED)
        self.assertEqual(commander_sug.confirmed_character, char)

        # Traceability check: mentions point to confirmed character
        for mention in commander_sug.mentions.all():
            self.assertEqual(mention.character, char)

    def test_merge_character_alias(self):
        version = import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )

        # Create canonical character
        cmd_char = confirm_character_suggestion(
            suggestion=version.character_suggestions.get(name="COMMANDER"),
            actor_membership=self.membership_a,
        )

        # Merge AGENT SMITH into COMMANDER
        smith_sug = version.character_suggestions.get(name="AGENT SMITH")
        merge_character_alias(
            suggestion=smith_sug,
            target_character=cmd_char,
            actor_membership=self.membership_a,
        )

        self.assertEqual(smith_sug.status, ScriptCharacterSuggestion.Status.MERGED)
        self.assertEqual(smith_sug.confirmed_character, cmd_char)

    def test_reject_false_positive_suggestion(self):
        version = import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )
        smith_sug = version.character_suggestions.get(name="AGENT SMITH")

        reject_character_suggestion(
            suggestion=smith_sug,
            actor_membership=self.membership_a,
        )

        self.assertEqual(smith_sug.status, ScriptCharacterSuggestion.Status.REJECTED)

    def test_cross_project_character_isolation(self):
        version_a = import_script_document(
            project=self.project_a,
            title="Script A",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )
        sug_a = version_a.character_suggestions.first()

        # Attempt to confirm suggestion in Project A using Project B membership
        with self.assertRaises(PermissionDenied):
            confirm_character_suggestion(
                suggestion=sug_a,
                actor_membership=self.membership_b,
            )

    def test_production_planning_matrix_coverage_and_status_precedence(self):
        version = import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )

        scenes = list(self.project_a.acts.first().sequences.first().scenes.all())
        scene1 = scenes[0]

        # Create Task in Scene 1
        task1 = create_task_from_script_selection(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=version,
            start_segment=version.segments.first(),
            end_segment=version.segments.all()[1],
            code="TASK-SCENE-1",
            title="Scene 1 Task",
            task_type="video",
        )

        matrix = get_production_planning_matrix(project=self.project_a)

        self.assertEqual(matrix["total_scenes"], len(scenes))
        self.assertGreater(matrix["coverage_pct"], 0.0)
        self.assertEqual(matrix["unresolved_character_mentions_count"], 2)

    def test_duplicate_task_warnings_detection(self):
        version = import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )

        seg1 = version.segments.first()

        # Create two tasks with same task_type in same scene
        task_a = create_task_from_script_selection(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=version,
            start_segment=seg1,
            end_segment=seg1,
            code="TASK-DUP-1",
            title="Video Task 1",
            task_type="video",
        )
        task_b = create_task_from_script_selection(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=version,
            start_segment=seg1,
            end_segment=seg1,
            code="TASK-DUP-2",
            title="Video Task 2",
            task_type="video",
        )

        matrix = get_production_planning_matrix(project=self.project_a)

        self.assertGreaterEqual(len(matrix["duplicate_warnings"]), 1)
        self.assertIn("Multiple video tasks created", matrix["duplicate_warnings"][0]["message"])

    def test_matrix_view_rendering(self):
        self.client.force_login(self.user_dir)

        import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )

        resp = self.client.get(reverse("production_matrix", kwargs={"slug": self.project_a.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Production Planning Matrix")
        self.assertContains(resp, "Script Coverage")
