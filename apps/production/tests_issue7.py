from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.production.models import (
    CoveragePlan,
    EditorialWarningWaiver,
    ProductionTask,
    ShotDefinition,
    ShotTaskLink,
)
from apps.projects.models import Department, Project
from services.production_matrix_services import get_production_planning_matrix
from services.project_services import create_project_with_defaults
from services.script_services import import_script_document
from services.shot_planning_services import (
    create_coverage_plan_with_shots,
    create_task_from_shot,
    detect_editorial_completeness_warnings,
    generate_coverage_plan_suggestions,
    waive_editorial_warning,
)

User = get_user_model()


class Issue7ShotPlanningAndCoverageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_dir = User.objects.create_user(username="issue7_dir", password="Password123!")
        self.user_other = User.objects.create_user(username="issue7_other", password="Password123!")

        self.project_a = create_project_with_defaults(
            creator_user=self.user_dir, name="Issue 7 Film A", synopsis="Project A"
        )
        self.project_b = create_project_with_defaults(
            creator_user=self.user_other, name="Issue 7 Film B", synopsis="Project B"
        )

        self.membership_a = self.project_a.memberships.get(user=self.user_dir)
        self.membership_b = self.project_b.memberships.get(user=self.user_other)

        self.script_text = (
            "INT. CONTROL ROOM - NIGHT\n"
            "COMMANDER\n"
            "Initiate neural link.\n"
            "AGENT SMITH\n"
            "Understood, Commander."
        )

        self.version_a = import_script_document(
            project=self.project_a,
            title="Script v1",
            raw_text=self.script_text,
            creator_membership=self.membership_a,
        )

    def test_generate_coverage_plan_suggestions(self):
        segments = list(self.version_a.segments.all())
        suggestions = generate_coverage_plan_suggestions(
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
        )

        categories = [s["shot_category"] for s in suggestions]
        self.assertIn(ShotDefinition.Category.MASTER, categories)
        self.assertIn(ShotDefinition.Category.OTS, categories)
        self.assertIn(ShotDefinition.Category.CLOSE_UP, categories)
        self.assertIn(ShotDefinition.Category.REACTION, categories)

    def test_create_coverage_plan_with_shots(self):
        segments = list(self.version_a.segments.all())
        suggestions = generate_coverage_plan_suggestions(
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
        )

        plan = create_coverage_plan_with_shots(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
            title="Control Room Scene Coverage",
            shot_specs=suggestions,
            editorial_strategy="Master two-shot, tight OTS, close-up performance",
        )

        self.assertEqual(plan.title, "Control Room Scene Coverage")
        self.assertEqual(plan.shots.count(), len(suggestions))
        self.assertEqual(plan.segment_links.first().text_snapshot.strip(), self.script_text.strip())

    def test_create_task_from_shot_linkage(self):
        segments = list(self.version_a.segments.all())
        suggestions = generate_coverage_plan_suggestions(
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
        )
        plan = create_coverage_plan_with_shots(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
            title="Coverage Plan",
            shot_specs=suggestions,
        )

        master_shot = plan.shots.get(shot_category=ShotDefinition.Category.MASTER)
        dept = self.project_a.departments.first()

        task = create_task_from_shot(
            shot=master_shot,
            actor_membership=self.membership_a,
            department=dept,
            task_type="video",
            code="TASK-SHOT-01",
            title="Generate Master Shot Video",
        )

        self.assertEqual(task.code, "TASK-SHOT-01")
        self.assertTrue(master_shot.task_links.filter(task=task).exists())

    def test_editorial_completeness_warnings_and_director_waiver(self):
        segments = list(self.version_a.segments.all())

        # Create incomplete plan without master shot
        custom_specs = [{
            "shot_code": "SHOT-01",
            "title": "OTS Shot Only",
            "shot_category": ShotDefinition.Category.OTS,
            "sequence_order": 1,
            "is_required": True,
        }]

        plan = create_coverage_plan_with_shots(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
            title="Incomplete Plan",
            shot_specs=custom_specs,
        )

        warnings = detect_editorial_completeness_warnings(coverage_plan=plan)
        codes = [w["code"] for w in warnings]

        self.assertIn("NO_MASTER_SHOT", codes)

        # Director waives warning
        waiver = waive_editorial_warning(
            coverage_plan=plan,
            warning_code="NO_MASTER_SHOT",
            reason="Style decision: handheld OTS tight framing used for intimacy.",
            actor_membership=self.membership_a,
        )

        self.assertIsInstance(waiver, EditorialWarningWaiver)

        # Re-evaluate warnings
        updated_warnings = detect_editorial_completeness_warnings(coverage_plan=plan)
        updated_codes = [w["code"] for w in updated_warnings]
        self.assertNotIn("NO_MASTER_SHOT", updated_codes)

    def test_cross_project_isolation(self):
        segments = list(self.version_a.segments.all())

        # Attempt to create coverage plan in Project A using Project B member
        with self.assertRaises(PermissionDenied):
            create_coverage_plan_with_shots(
                project=self.project_a,
                actor_membership=self.membership_b,
                script_version=self.version_a,
                start_segment=segments[0],
                end_segment=segments[-1],
                title="Cross Project Plan",
                shot_specs=[],
            )

    def test_matrix_reflects_shot_metrics(self):
        segments = list(self.version_a.segments.all())
        suggestions = generate_coverage_plan_suggestions(
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
        )
        plan = create_coverage_plan_with_shots(
            project=self.project_a,
            actor_membership=self.membership_a,
            script_version=self.version_a,
            start_segment=segments[0],
            end_segment=segments[-1],
            title="Plan with shots",
            shot_specs=suggestions,
        )

        matrix = get_production_planning_matrix(project=self.project_a)
        self.assertEqual(matrix["total_shots_count"], len(suggestions))
