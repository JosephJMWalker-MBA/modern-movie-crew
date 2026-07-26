import re
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.characters.models import Character
from apps.core.models import AuditEvent
from apps.production.models import (
    ScriptCharacterMention,
    ScriptCharacterSuggestion,
    ScriptSegment,
    ScriptVersion,
)
from services.boundary_services import verify_membership_in_project
from services.character_services import create_character_with_identity

CHARACTER_SPEAKER_CLEANER = re.compile(r"\s*\((V\.O\.|O\.S\.|CONT'D|CONTINUED|OFF|VOICE)\)", re.IGNORECASE)
RAW_NAME_VALIDATOR = re.compile(r"^[A-Z0-9\s\'\.\-]{2,40}$")


def normalize_character_name(raw_name: str) -> str:
    cleaned = CHARACTER_SPEAKER_CLEANER.sub("", raw_name).strip()
    return cleaned.upper()


@transaction.atomic
def analyze_script_for_character_suggestions(*, script_version: ScriptVersion):
    """
    Scans ScriptVersion segments to extract character suggestions deterministically.
    Never creates canonical characters automatically.
    """
    project = script_version.script_document.project
    segments = script_version.segments.all()

    found_mentions_by_name = {}  # { normalized_name: [ (segment, raw_name) ] }

    for seg in segments:
        if seg.segment_type == ScriptSegment.SegmentType.DIALOGUE:
            lines = [line.strip() for line in seg.text_content.splitlines() if line.strip()]
            if lines:
                speaker_line = lines[0]
                norm_name = normalize_character_name(speaker_line)
                if norm_name and RAW_NAME_VALIDATOR.match(norm_name):
                    found_mentions_by_name.setdefault(norm_name, []).append((seg, speaker_line))

    created_suggestions = []
    for norm_name, mentions_list in found_mentions_by_name.items():
        raw_name = mentions_list[0][1]
        count = len(mentions_list)

        # Check if already confirmed/merged/rejected in prior runs
        existing_char = project.characters.filter(name__iexact=norm_name).first()
        init_status = (
            ScriptCharacterSuggestion.Status.CONFIRMED
            if existing_char
            else ScriptCharacterSuggestion.Status.SUGGESTED
        )

        sug, _ = ScriptCharacterSuggestion.objects.get_or_create(
            script_version=script_version,
            name=norm_name,
            defaults={
                "raw_name": raw_name,
                "status": init_status,
                "confirmed_character": existing_char,
                "occurrence_count": count,
            },
        )
        if sug.occurrence_count != count:
            sug.occurrence_count = count
            sug.save()

        # Link mentions
        for seg, r_name in mentions_list:
            ScriptCharacterMention.objects.get_or_create(
                suggestion=sug,
                segment=seg,
                defaults={"character": existing_char},
            )

        created_suggestions.append(sug)

    return created_suggestions


@transaction.atomic
def confirm_character_suggestion(
    *,
    suggestion: ScriptCharacterSuggestion,
    actor_membership,
    custom_name: str = "",
) -> Character:
    project = suggestion.script_version.script_document.project
    verify_membership_in_project(membership=actor_membership, project=project)

    target_name = (custom_name.strip() or suggestion.name).upper()

    character = project.characters.filter(name__iexact=target_name).first()
    if not character:
        character = create_character_with_identity(
            project=project,
            creator_membership=actor_membership,
            name=target_name,
            description=f"Confirmed from script workspace suggestion '{suggestion.name}'",
        )

    suggestion.status = ScriptCharacterSuggestion.Status.CONFIRMED
    suggestion.confirmed_character = character
    suggestion.save()

    # Link mentions to character
    suggestion.mentions.all().update(character=character)

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="character_suggestion_confirmed",
        object_type="script_character_suggestion",
        object_id=str(suggestion.id),
        metadata={"character_name": character.name},
    )

    return character


@transaction.atomic
def merge_character_alias(
    *,
    suggestion: ScriptCharacterSuggestion,
    target_character: Character,
    actor_membership,
) -> ScriptCharacterSuggestion:
    project = suggestion.script_version.script_document.project
    verify_membership_in_project(membership=actor_membership, project=project)
    if target_character.project_id != project.id:
        raise ValidationError("Target character must belong to the same project.")

    suggestion.status = ScriptCharacterSuggestion.Status.MERGED
    suggestion.confirmed_character = target_character
    suggestion.save()

    suggestion.mentions.all().update(character=target_character)

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="character_alias_merged",
        object_type="script_character_suggestion",
        object_id=str(suggestion.id),
        metadata={"alias_name": suggestion.name, "target_character": target_character.name},
    )

    return suggestion


@transaction.atomic
def reject_character_suggestion(
    *,
    suggestion: ScriptCharacterSuggestion,
    actor_membership,
) -> ScriptCharacterSuggestion:
    project = suggestion.script_version.script_document.project
    verify_membership_in_project(membership=actor_membership, project=project)

    suggestion.status = ScriptCharacterSuggestion.Status.REJECTED
    suggestion.save()

    AuditEvent.objects.create(
        project=project,
        actor=actor_membership,
        event_type="character_suggestion_rejected",
        object_type="script_character_suggestion",
        object_id=str(suggestion.id),
        metadata={"rejected_name": suggestion.name},
    )

    return suggestion
