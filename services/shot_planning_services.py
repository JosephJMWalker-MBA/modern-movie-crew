from django.core.exceptions import ValidationError
from django.db import transaction

from apps.characters.models import Character
from apps.core.models import AuditEvent
from apps.production.models import (
    CoveragePlan,
    CoveragePlanSegmentLink,
    EditorialWarningWaiver,
    ProductionTask,
    ScriptSegment,
    ScriptVersion,
    ShotDefinition,
    ShotTaskLink,
)
from services.boundary_services import verify_director_authority, verify_membership_in_project
from services.production_services import create_production_task_with_packet


def generate_coverage_plan_suggestions(*, script_version: ScriptVersion, start_segment: ScriptSegment, end_segment: ScriptSegment) -> list:
    """
    Analyzes a ScriptSegment range deterministically and proposes standard shot coverage templates.
    """
    segments = ScriptSegment.objects.filter(
        script_version=script_version,
        segment_number__gte=start_segment.segment_number,
        segment_number__lte=end_segment.segment_number,
    ).order_by("segment_number")

    has_dialogue = any(s.segment_type == ScriptSegment.SegmentType.DIALOGUE for s in segments)
    has_heading = any(s.segment_type == ScriptSegment.SegmentType.SCENE_HEADING for s in segments)
    has_action = any(s.segment_type == ScriptSegment.SegmentType.ACTION for s in segments)

    shot_specs = []
    seq = 1

    if has_heading:
        shot_specs.append({
            "shot_code": f"SHOT-{seq:02d}",
            "title": "Establishing Shot",
            "shot_category": ShotDefinition.Category.ESTABLISHING,
            "editorial_purpose": "Establish scene location, atmosphere, and spatial layout.",
            "sequence_order": seq,
            "is_required": True,
        })
        seq += 1

    if has_dialogue:
        shot_specs.append({
            "shot_code": f"SHOT-{seq:02d}",
            "title": "Master Two-Shot",
            "shot_category": ShotDefinition.Category.MASTER,
            "editorial_purpose": "Master coverage of speaking characters and action beat.",
            "sequence_order": seq,
            "is_required": True,
        })
        seq += 1

        shot_specs.append({
            "shot_code": f"SHOT-{seq:02d}",
            "title": "Over-the-Shoulder Coverage",
            "shot_category": ShotDefinition.Category.OTS,
            "editorial_purpose": "Over-the-shoulder framing for dialogue exchanges.",
            "sequence_order": seq,
            "is_required": True,
        })
        seq += 1

        shot_specs.append({
            "shot_code": f"SHOT-{seq:02d}",
            "title": "Character Close-up",
            "shot_category": ShotDefinition.Category.CLOSE_UP,
            "editorial_purpose": "Close-up facial performance for key line delivery.",
            "sequence_order": seq,
            "is_required": True,
        })
        seq += 1

        shot_specs.append({
            "shot_code": f"SHOT-{seq:02d}",
            "title": "Listener Reaction Shot",
            "shot_category": ShotDefinition.Category.REACTION,
            "editorial_purpose": "Emotional reaction of listening character during key dialogue.",
            "sequence_order": seq,
            "is_required": False,
        })
        seq += 1

    if has_action:
        shot_specs.append({
            "shot_code": f"SHOT-{seq:02d}",
            "title": "Action Insert Shot",
            "shot_category": ShotDefinition.Category.INSERT,
            "editorial_purpose": "Tight insert of key object or action detail.",
            "sequence_order": seq,
            "is_required": True,
        })
        seq += 1

    # Sound & Environmental B-roll
    shot_specs.append({
        "shot_code": f"SHOT-{seq:02d}",
        "title": "Environmental B-Roll & Room Tone",
        "shot_category": ShotDefinition.Category.B_ROLL,
        "editorial_purpose": "Cutaway ambient visuals and room tone audio track.",
        "sequence_order": seq,
        "is_required": False,
    })

    return shot_specs


@transaction.atomic
def create_coverage_plan_with_shots(
    *,
    project,
    actor_membership,
    script_version: ScriptVersion,
    start_segment: ScriptSegment,
    end_segment: ScriptSegment,
    title: str,
    shot_specs: list,
    editorial_strategy: str = "",
) -> CoveragePlan:
    """
    Creates a governed CoveragePlan, links source script segments, and creates child ShotDefinitions.
    """
    verify_membership_in_project(membership=actor_membership, project=project)
    if script_version.script_document.project_id != project.id:
        raise ValidationError("ScriptVersion does not belong to target project.")

    if start_segment.script_version_id != script_version.id or end_segment.script_version_id != script_version.id:
        raise ValidationError("Segments must belong to specified script version.")

    if start_segment.segment_number > end_segment.segment_number:
        raise ValidationError("Start segment cannot be after end segment.")

    segments = ScriptSegment.objects.filter(
        script_version=script_version,
        segment_number__gte=start_segment.segment_number,
        segment_number__lte=end_segment.segment_number,
    ).order_by("segment_number")

    snippet = "\n".join(s.text_content for s in segments)

    plan = CoveragePlan.objects.create(
        project=project,
        script_version=script_version,
        title=title,
        editorial_strategy=editorial_strategy,
        created_by=actor_membership,
    )

    CoveragePlanSegmentLink.objects.create(
        coverage_plan=plan,
        start_segment=start_segment,
        end_segment=end_segment,
        text_snapshot=snippet,
    )

    for spec in shot_specs:
        ShotDefinition.objects.create(
            coverage_plan=plan,
            shot_code=spec["shot_code"],
            title=spec["title"],
            shot_category=spec.get("shot_category", ShotDefinition.Category.MEDIUM),
            editorial_purpose=spec.get("editorial_purpose", ""),
            framing_notes=spec.get("framing_notes", ""),
            camera_movement=spec.get("camera_movement", ""),
            lens_notes=spec.get("lens_notes", ""),
            duration_target_seconds=spec.get("duration_target_seconds", 5),
            sequence_order=spec.get("sequence_order", 1),
            is_required=spec.get("is_required", True),
            character=spec.get("character"),
            created_by=actor_membership,
        )

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="coverage_plan_created",
        object_type="coverage_plan",
        object_id=str(plan.id),
        metadata={"title": title, "shot_count": len(shot_specs)},
    )

    return plan


@transaction.atomic
def create_task_from_shot(
    *,
    shot: ShotDefinition,
    actor_membership,
    department,
    task_type: str = "video",
    code: str,
    title: str,
) -> ProductionTask:
    """
    Creates a governed ProductionTask linked to a ShotDefinition.
    """
    project = shot.coverage_plan.project
    verify_membership_in_project(membership=actor_membership, project=project)

    task = create_production_task_with_packet(
        project=project,
        actor_membership=actor_membership,
        code=code,
        title=title,
        task_type=task_type,
        character=shot.character,
    )

    ShotTaskLink.objects.create(
        shot=shot,
        task=task,
    )

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="task_created_from_shot",
        object_type="production_task",
        object_id=str(task.id),
        metadata={"shot_code": shot.shot_code, "task_code": code},
    )

    return task


def detect_editorial_completeness_warnings(*, coverage_plan: CoveragePlan) -> list:
    """
    Evaluates coverage plan against editorial completeness rules.
    Returns list of active warnings, excluding those with an active EditorialWarningWaiver.
    """
    warnings = []
    waived_codes = set(coverage_plan.warning_waivers.values_list("warning_code", flat=True))

    shots = list(coverage_plan.shots.all())
    categories = set(s.shot_category for s in shots)

    # 1. Missing Master Shot Warning
    if ShotDefinition.Category.MASTER not in categories:
        code = "NO_MASTER_SHOT"
        if code not in waived_codes:
            warnings.append({
                "code": code,
                "title": "Missing Master Shot",
                "message": "Dialogue coverage plan lacks a master shot to anchor spatial continuity.",
            })

    # 2. Missing Close-Up Warning
    if not (ShotDefinition.Category.CLOSE_UP in categories or ShotDefinition.Category.EXTREME_CLOSE_UP in categories):
        code = "NO_CLOSE_UP"
        if code not in waived_codes:
            warnings.append({
                "code": code,
                "title": "Missing Close-Up Coverage",
                "message": "Plan lacks close-up coverage for emotional emphasis.",
            })

    # 3. Required Shot with No Task
    unplanned_shots = [s for s in shots if s.is_required and not s.task_links.exists()]
    if unplanned_shots:
        code = "REQUIRED_SHOT_UNPLANNED"
        if code not in waived_codes:
            warnings.append({
                "code": code,
                "title": "Required Shots Missing Tasks",
                "message": f"{len(unplanned_shots)} required shot(s) have no production task created.",
            })

    # 4. Tasks without Accepted Assets
    unaccepted_tasks_count = 0
    for s in shots:
        for link in s.task_links.all():
            if not link.task.active_canonical_selection():
                unaccepted_tasks_count += 1

    if unaccepted_tasks_count > 0:
        code = "TASKS_UNACCEPTED"
        if code not in waived_codes:
            warnings.append({
                "code": code,
                "title": "Incomplete Asset Coverage",
                "message": f"{unaccepted_tasks_count} shot task(s) do not yet have an accepted canonical asset.",
            })

    # 5. Stale Coverage Plan Warning
    seg_link = coverage_plan.segment_links.first()
    if seg_link and seg_link.has_text_drifted():
        code = "STALE_COVERAGE_PLAN"
        if code not in waived_codes:
            warnings.append({
                "code": code,
                "title": "Script Revision Drift",
                "message": "Source script text has been modified since coverage plan creation.",
            })

    return warnings


@transaction.atomic
def waive_editorial_warning(
    *,
    coverage_plan: CoveragePlan,
    warning_code: str,
    reason: str,
    actor_membership,
) -> EditorialWarningWaiver:
    """
    Creates a Director waiver recording explicit rationale for bypassing an editorial warning.
    """
    project = coverage_plan.project
    verify_director_authority(reviewer=actor_membership, project=project)

    waiver, _ = EditorialWarningWaiver.objects.get_or_create(
        coverage_plan=coverage_plan,
        warning_code=warning_code,
        defaults={
            "project": project,
            "reason": reason,
            "waived_by": actor_membership,
        },
    )

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="editorial_warning_waived",
        object_type="editorial_warning_waiver",
        object_id=str(waiver.id),
        metadata={"warning_code": warning_code, "reason": reason},
    )

    return waiver
