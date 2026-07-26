import re
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.characters.models import Character
from apps.core.models import AuditEvent
from apps.production.models import (
    Act,
    ProductionTask,
    Scene,
    ScriptDocument,
    ScriptSegment,
    ScriptVersion,
    Sequence,
    TaskScriptLink,
)
from services.boundary_services import verify_membership_in_project
from services.character_discovery_services import analyze_script_for_character_suggestions
from services.production_services import create_production_task_with_packet

SCENE_HEADING_REGEX = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|EXT/INT\.|INT\s|EXT\s|SCENE\s)", re.IGNORECASE)
CHARACTER_HEADING_REGEX = re.compile(r"^[A-Z0-9\s\'\.\-\(\)]{2,40}$")


def parse_script_text_to_segments(*, script_version: ScriptVersion, project, raw_text: str):
    """
    Parses screenplay or manuscript raw text into sequential ScriptSegment objects.
    Automatically detects scene headings and manages Act -> Sequence -> Scene hierarchy.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return []

    act, _ = Act.objects.get_or_create(project=project, act_number=1, defaults={"title": "Act I"})
    seq, _ = Sequence.objects.get_or_create(act=act, sequence_number=1, defaults={"title": "Sequence A"})

    current_scene = Scene.objects.filter(sequence=seq).order_by("scene_number").last()
    if not current_scene:
        current_scene = Scene.objects.create(sequence=seq, scene_number=1, title="Scene 1")

    scene_count = current_scene.scene_number
    segment_number = 1
    segments_to_create = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # 1. Detect Scene Heading
        if SCENE_HEADING_REGEX.match(line):
            scene_count += 1
            current_scene = Scene.objects.create(
                sequence=seq,
                scene_number=scene_count,
                title=line[:200],
            )
            segments_to_create.append(
                ScriptSegment(
                    script_version=script_version,
                    segment_number=segment_number,
                    segment_type=ScriptSegment.SegmentType.SCENE_HEADING,
                    text_content=line,
                    scene=current_scene,
                )
            )
            segment_number += 1
            i += 1
            continue

        # 2. Detect Character Dialogue Block
        if (
            CHARACTER_HEADING_REGEX.match(line)
            and not line.startswith("(")
            and i + 1 < len(lines)
            and not SCENE_HEADING_REGEX.match(lines[i + 1])
        ):
            char_name = line.strip().upper()
            character_obj = project.characters.filter(name__iexact=char_name).first()

            dialogue_text = lines[i + 1]
            combined_dialogue = f"{line}\n{dialogue_text}"

            segments_to_create.append(
                ScriptSegment(
                    script_version=script_version,
                    segment_number=segment_number,
                    segment_type=ScriptSegment.SegmentType.DIALOGUE,
                    text_content=combined_dialogue,
                    scene=current_scene,
                    character=character_obj,
                )
            )
            segment_number += 1
            i += 2
            continue

        # 3. Default Action / Paragraph Block
        segments_to_create.append(
            ScriptSegment(
                script_version=script_version,
                segment_number=segment_number,
                segment_type=ScriptSegment.SegmentType.ACTION,
                text_content=line,
                scene=current_scene,
            )
        )
        segment_number += 1
        i += 1

    return ScriptSegment.objects.bulk_create(segments_to_create)


@transaction.atomic
def import_script_document(
    *,
    project,
    title: str,
    raw_text: str,
    creator_membership,
    description: str = "",
) -> ScriptVersion:
    """Imports a raw screenplay text document and generates initial ScriptVersion v1 with parsed segments."""
    verify_membership_in_project(membership=creator_membership, project=project)

    doc = ScriptDocument.objects.create(
        project=project,
        title=title,
        description=description,
        created_by=creator_membership,
    )

    version = ScriptVersion.objects.create(
        script_document=doc,
        version_number=1,
        raw_text=raw_text,
        created_by=creator_membership,
    )

    parse_script_text_to_segments(script_version=version, project=project, raw_text=raw_text)

    # Run deterministic Python character suggestion analysis
    analyze_script_for_character_suggestions(script_version=version)

    AuditEvent.objects.create(
        project=project,
        actor=creator_membership,
        event_type="script_imported",
        object_type="script_version",
        object_id=str(version.id),
        metadata={"script_title": title, "version_number": 1},
    )

    return version


@transaction.atomic
def create_task_from_script_selection(
    *,
    project,
    actor_membership,
    script_version: ScriptVersion,
    start_segment: ScriptSegment,
    end_segment: ScriptSegment,
    code: str,
    title: str,
    task_type: str = "video",
    character: Character = None,
) -> ProductionTask:
    """Creates a governed ProductionTask linked to a range of ScriptSegment objects in a ScriptVersion."""
    verify_membership_in_project(membership=actor_membership, project=project)
    if script_version.script_document.project_id != project.id:
        raise ValidationError("Script version does not belong to target project.")

    if start_segment.script_version_id != script_version.id or end_segment.script_version_id != script_version.id:
        raise ValidationError("Segments must belong to specified script version.")

    if start_segment.segment_number > end_segment.segment_number:
        raise ValidationError("Start segment cannot be after end segment.")

    # Gather selected segment text
    segments = ScriptSegment.objects.filter(
        script_version=script_version,
        segment_number__gte=start_segment.segment_number,
        segment_number__lte=end_segment.segment_number,
    ).order_by("segment_number")

    snippet = "\n".join(s.text_content for s in segments)

    task = create_production_task_with_packet(
        project=project,
        actor_membership=actor_membership,
        code=code,
        title=title,
        task_type=task_type,
        character=character,
    )

    # Link script segments
    TaskScriptLink.objects.create(
        task=task,
        script_version=script_version,
        start_segment=start_segment,
        end_segment=end_segment,
        segment_text_snapshot=snippet,
    )

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="task_created_from_script",
        object_type="production_task",
        object_id=str(task.id),
        metadata={"task_code": code, "script_version": script_version.version_number},
    )

    return task
