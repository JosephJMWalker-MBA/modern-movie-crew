from django.core.exceptions import ValidationError
from django.db import models


class Act(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        related_name="acts",
        on_delete=models.CASCADE,
    )
    act_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("project", "act_number")
        ordering = ("act_number",)

    def __str__(self):
        return f"Act {self.act_number}: {self.title or 'Untitled'}"


class Sequence(models.Model):
    act = models.ForeignKey(
        Act,
        related_name="sequences",
        on_delete=models.CASCADE,
    )
    sequence_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)
    sequence_rules = models.TextField(blank=True)

    class Meta:
        unique_together = ("act", "sequence_number")
        ordering = ("sequence_number",)

    def __str__(self):
        return f"Sequence {self.sequence_number}: {self.title or 'Untitled'}"


class Scene(models.Model):
    sequence = models.ForeignKey(
        Sequence,
        related_name="scenes",
        on_delete=models.CASCADE,
    )
    scene_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("sequence", "scene_number")
        ordering = ("scene_number",)

    def __str__(self):
        return f"Scene {self.scene_number}: {self.title or 'Untitled'}"


class ProductionTask(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready to open"
        OPEN = "open", "Open"
        SATISFIED = "satisfied", "Satisfied"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class ClaimMode(models.TextChoices):
        SINGLE = "single", "One contributor"
        OPEN_CALL = "open_call", "Open call"

    project = models.ForeignKey(
        "projects.Project",
        related_name="tasks",
        on_delete=models.CASCADE,
    )
    scene = models.ForeignKey(
        Scene,
        related_name="tasks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    code = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    task_type = models.CharField(max_length=60)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    claim_mode = models.CharField(
        max_length=20,
        choices=ClaimMode.choices,
        default=ClaimMode.SINGLE,
    )

    class Meta:
        unique_together = ("project", "code")

    def clean(self):
        if (
            self.scene_id
            and self.scene.sequence.act.project_id != self.project_id
        ):
            raise ValidationError(
                "Scene and ProductionTask must belong to the same project."
            )

        if self.pk and self.status in [self.Status.READY, self.Status.OPEN]:
            # Verify packet sections
            unapproved_required_sections = self.packet_sections.filter(
                required=True
            ).exclude(status="approved")
            if unapproved_required_sections.exists():
                raise ValidationError(
                    "All required packet sections must be approved before task can transition to READY or OPEN."
                )

            # Verify character links have approved identity versions
            for link in self.character_links.all():
                if link.character_identity_version.status != "approved":
                    raise ValidationError(
                        f"Character {link.character.name} identity version must be APPROVED before task can transition to READY or OPEN."
                    )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def active_canonical_selection(self):
        return self.canonical_selections.filter(retired_at__isnull=True).first()

    def __str__(self):
        return f"Task {self.code}: {self.title} [{self.status}]"


class PacketSection(models.Model):
    class SectionType(models.TextChoices):
        STORY = "story", "Story and action"
        PERFORMANCE = "performance", "Performance"
        WARDROBE = "wardrobe", "Wardrobe"
        SET = "set", "Set and props"
        CAMERA = "camera", "Camera and lighting"
        CONTINUITY = "continuity", "Continuity"
        GENERATION = "generation", "Generation instructions"
        FINAL_PROMPT = "final_prompt", "External prompt"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Awaiting approval"
        APPROVED = "approved", "Approved"
        REVISION = "revision", "Revision requested"

    task = models.ForeignKey(
        ProductionTask,
        related_name="packet_sections",
        on_delete=models.CASCADE,
    )
    department = models.ForeignKey(
        "projects.Department",
        related_name="packet_sections",
        on_delete=models.PROTECT,
    )
    section_type = models.CharField(
        max_length=30,
        choices=SectionType.choices,
    )
    content = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    approved_by = models.ForeignKey(
        "projects.Membership",
        related_name="approved_packet_sections",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("task", "section_type")

    def clean(self):
        if (
            self.task_id
            and self.department_id
            and self.department.project_id != self.task.project_id
        ):
            raise ValidationError(
                "Department must belong to the same project as ProductionTask."
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task.code} Packet: {self.section_type} [{self.status}]"


class Resource(models.Model):
    class Kind(models.TextChoices):
        SCRIPT = "script", "Script"
        CHARACTER = "character", "Character reference"
        WARDROBE = "wardrobe", "Wardrobe reference"
        SET = "set", "Set reference"
        PROP = "prop", "Prop reference"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        MUSIC = "music", "Music"
        DOCUMENT = "document", "Document"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Under review"
        APPROVED = "approved", "Approved"
        DEPRECATED = "deprecated", "Deprecated"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(
        "projects.Project",
        related_name="resources",
        on_delete=models.CASCADE,
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    storage_key = models.CharField(max_length=500, blank=True)
    external_url = models.URLField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        "projects.Membership",
        related_name="created_resources",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resource: {self.title} ({self.kind})"


class TaskResource(models.Model):
    task = models.ForeignKey(
        ProductionTask,
        related_name="resource_links",
        on_delete=models.CASCADE,
    )
    resource = models.ForeignKey(
        Resource,
        related_name="task_links",
        on_delete=models.PROTECT,
    )
    purpose = models.CharField(max_length=200, blank=True)
    required = models.BooleanField(default=True)

    class Meta:
        unique_together = ("task", "resource")

    def clean(self):
        if (
            self.task_id
            and self.resource_id
            and self.task.project_id != self.resource.project_id
        ):
            raise ValidationError(
                "Task and Resource must belong to the same project."
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task.code} -> {self.resource.title}"


class TaskClaim(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUBMITTED = "submitted", "Submitted"
        EXPIRED = "expired", "Expired"
        RELEASED = "released", "Released"

    task = models.ForeignKey(
        ProductionTask,
        related_name="claims",
        on_delete=models.CASCADE,
    )
    contributor = models.ForeignKey(
        "projects.Membership",
        related_name="task_claims",
        on_delete=models.PROTECT,
    )
    claimed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    def clean(self):
        if (
            self.task_id
            and self.contributor_id
            and self.task.project_id != self.contributor.project_id
        ):
            raise ValidationError(
                "Task and Contributor must belong to the same project."
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Claim by {self.contributor.credited_name} on {self.task.code} [{self.status}]"


class CharacterTaskLink(models.Model):
    task = models.ForeignKey(
        ProductionTask,
        related_name="character_links",
        on_delete=models.CASCADE,
    )
    character = models.ForeignKey(
        "characters.Character",
        related_name="task_links",
        on_delete=models.CASCADE,
    )
    character_identity_version = models.ForeignKey(
        "characters.CharacterIdentityVersion",
        related_name="task_links",
        on_delete=models.PROTECT,
    )
    character_look = models.ForeignKey(
        "characters.CharacterLook",
        null=True,
        blank=True,
        related_name="task_links",
        on_delete=models.PROTECT,
    )
    character_scene_state = models.ForeignKey(
        "characters.CharacterSceneState",
        null=True,
        blank=True,
        related_name="task_links",
        on_delete=models.PROTECT,
    )
    voice_profile = models.ForeignKey(
        "characters.VoiceProfile",
        null=True,
        blank=True,
        related_name="task_links",
        on_delete=models.PROTECT,
    )
    performance_profile = models.ForeignKey(
        "characters.PerformanceProfile",
        null=True,
        blank=True,
        related_name="task_links",
        on_delete=models.PROTECT,
    )

    class Meta:
        unique_together = ("task", "character")

    def clean(self):
        if not (self.task_id and self.character_id and self.character_identity_version_id):
            return

        if self.character.project_id != self.task.project_id:
            raise ValidationError(
                "Task and Character must belong to the same project."
            )

        if self.character_identity_version.character_id != self.character_id:
            raise ValidationError(
                "CharacterIdentityVersion does not belong to the linked Character."
            )

        if self.character_look and self.character_look.character_id != self.character_id:
            raise ValidationError(
                "CharacterLook does not belong to the linked Character."
            )

        if self.voice_profile and self.voice_profile.character_id != self.character_id:
            raise ValidationError(
                "VoiceProfile does not belong to the linked Character."
            )

        if self.performance_profile and self.performance_profile.character_id != self.character_id:
            raise ValidationError(
                "PerformanceProfile does not belong to the linked Character."
            )

        if self.character_scene_state:
            if self.character_scene_state.character_id != self.character_id:
                raise ValidationError(
                    "CharacterSceneState does not belong to the linked Character."
                )
            if self.task.scene_id and self.character_scene_state.scene_id != self.task.scene_id:
                raise ValidationError(
                    "CharacterSceneState must match the task's scene."
                )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task.code} -> Character: {self.character.name}"


# SCRIPT IMPORT & SCRIPT-FIRST PRODUCTION PLANNING ENTITIES

class ScriptDocument(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        related_name="script_documents",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "projects.Membership",
        related_name="created_script_documents",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Script: {self.title} ({self.project.name})"


class ScriptVersion(models.Model):
    script_document = models.ForeignKey(
        ScriptDocument,
        related_name="versions",
        on_delete=models.CASCADE,
    )
    version_number = models.PositiveIntegerField()
    raw_text = models.TextField()
    parsed_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "projects.Membership",
        related_name="created_script_versions",
        on_delete=models.PROTECT,
    )

    class Meta:
        unique_together = ("script_document", "version_number")
        ordering = ("-version_number",)

    def clean(self):
        if self.pk:
            raise ValidationError("ScriptVersion records are immutable once created.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("ScriptVersion records are immutable once created.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("ScriptVersion records are immutable and cannot be deleted.")

    def __str__(self):
        return f"{self.script_document.title} v{self.version_number}"


class ScriptSegment(models.Model):
    class SegmentType(models.TextChoices):
        SCENE_HEADING = "scene_heading", "Scene Heading"
        ACTION = "action", "Action"
        DIALOGUE = "dialogue", "Dialogue"
        PARENTHETICAL = "parenthetical", "Parenthetical"
        TRANSITION = "transition", "Transition"
        PARAGRAPH = "paragraph", "Paragraph"

    script_version = models.ForeignKey(
        ScriptVersion,
        related_name="segments",
        on_delete=models.CASCADE,
    )
    segment_number = models.PositiveIntegerField()
    segment_type = models.CharField(max_length=30, choices=SegmentType.choices)
    text_content = models.TextField()
    scene = models.ForeignKey(
        Scene,
        null=True,
        blank=True,
        related_name="script_segments",
        on_delete=models.SET_NULL,
    )
    character = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        related_name="script_segments",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ("segment_number",)
        unique_together = ("script_version", "segment_number")

    def __str__(self):
        return f"Segment #{self.segment_number} [{self.segment_type}]"


class TaskScriptLink(models.Model):
    task = models.ForeignKey(
        ProductionTask,
        related_name="script_links",
        on_delete=models.CASCADE,
    )
    script_version = models.ForeignKey(
        ScriptVersion,
        related_name="task_links",
        on_delete=models.PROTECT,
    )
    start_segment = models.ForeignKey(
        ScriptSegment,
        related_name="starting_task_links",
        on_delete=models.PROTECT,
    )
    end_segment = models.ForeignKey(
        ScriptSegment,
        related_name="ending_task_links",
        on_delete=models.PROTECT,
    )
    segment_text_snapshot = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.start_segment.script_version_id != self.script_version_id or self.end_segment.script_version_id != self.script_version_id:
            raise ValidationError("Start and End segments must belong to the linked ScriptVersion.")
        if self.start_segment.segment_number > self.end_segment.segment_number:
            raise ValidationError("start_segment cannot be after end_segment.")
        if self.task.project_id != self.script_version.script_document.project_id:
            raise ValidationError("Task and ScriptVersion must belong to the same project.")

    def has_text_drifted(self) -> bool:
        segments = ScriptSegment.objects.filter(
            script_version=self.script_version,
            segment_number__gte=self.start_segment.segment_number,
            segment_number__lte=self.end_segment.segment_number,
        ).order_by("segment_number")
        current_text = "\n".join(s.text_content for s in segments)
        return current_text.strip() != self.segment_text_snapshot.strip()

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task.code} -> Script v{self.script_version.version_number} Segments #{self.start_segment.segment_number}-{self.end_segment.segment_number}"


class ScriptCharacterSuggestion(models.Model):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        CONFIRMED = "confirmed", "Confirmed"
        MERGED = "merged", "Merged"
        REJECTED = "rejected", "Rejected"

    script_version = models.ForeignKey(
        ScriptVersion,
        related_name="character_suggestions",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=120)
    raw_name = models.CharField(max_length=120)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUGGESTED,
        db_index=True,
    )
    confirmed_character = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        related_name="script_suggestions",
        on_delete=models.SET_NULL,
    )
    occurrence_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("script_version", "name")
        ordering = ("-occurrence_count", "name")

    def __str__(self):
        return f"Suggestion: {self.name} ({self.status}) [{self.occurrence_count}x]"


class ScriptCharacterMention(models.Model):
    suggestion = models.ForeignKey(
        ScriptCharacterSuggestion,
        related_name="mentions",
        on_delete=models.CASCADE,
    )
    segment = models.ForeignKey(
        ScriptSegment,
        related_name="character_mentions",
        on_delete=models.CASCADE,
    )
    character = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        related_name="script_mentions",
        on_delete=models.SET_NULL,
    )

    class Meta:
        unique_together = ("suggestion", "segment")

    def clean(self):
        if self.suggestion.script_version_id != self.segment.script_version_id:
            raise ValidationError("Suggestion and Segment must belong to the same ScriptVersion.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Mention: {self.suggestion.name} at Segment #{self.segment.segment_number}"


# SHOT PLANNING & COVERAGE PLAN ENTITIES (Issue #7)

class CoveragePlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        STALE = "stale", "Stale (Script Changed)"
        RETIRED = "retired", "Retired"

    project = models.ForeignKey(
        "projects.Project",
        related_name="coverage_plans",
        on_delete=models.CASCADE,
    )
    script_version = models.ForeignKey(
        ScriptVersion,
        related_name="coverage_plans",
        on_delete=models.PROTECT,
    )
    title = models.CharField(max_length=200)
    editorial_strategy = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        "projects.Membership",
        related_name="created_coverage_plans",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CoveragePlan: {self.title} [{self.status}]"


class CoveragePlanSegmentLink(models.Model):
    coverage_plan = models.ForeignKey(
        CoveragePlan,
        related_name="segment_links",
        on_delete=models.CASCADE,
    )
    start_segment = models.ForeignKey(
        ScriptSegment,
        related_name="starting_coverage_links",
        on_delete=models.PROTECT,
    )
    end_segment = models.ForeignKey(
        ScriptSegment,
        related_name="ending_coverage_links",
        on_delete=models.PROTECT,
    )
    text_snapshot = models.TextField()

    def clean(self):
        if self.start_segment.script_version_id != self.coverage_plan.script_version_id or self.end_segment.script_version_id != self.coverage_plan.script_version_id:
            raise ValidationError("Segments must belong to the coverage plan's ScriptVersion.")

    def has_text_drifted(self) -> bool:
        segments = ScriptSegment.objects.filter(
            script_version=self.coverage_plan.script_version,
            segment_number__gte=self.start_segment.segment_number,
            segment_number__lte=self.end_segment.segment_number,
        ).order_by("segment_number")
        current_text = "\n".join(s.text_content for s in segments)
        return current_text.strip() != self.text_snapshot.strip()

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class ShotDefinition(models.Model):
    class Category(models.TextChoices):
        MASTER = "master", "Master Shot"
        WIDE = "wide", "Wide Shot"
        MEDIUM = "medium", "Medium Shot"
        CLOSE_UP = "close_up", "Close-up"
        EXTREME_CLOSE_UP = "extreme_close_up", "Extreme Close-up"
        OTS = "ots", "Over-the-Shoulder"
        TWO_SHOT = "two_shot", "Two-Shot"
        REACTION = "reaction", "Reaction Shot"
        INSERT = "insert", "Insert"
        CUTAWAY = "cutaway", "Cutaway"
        ESTABLISHING = "establishing", "Establishing Shot"
        TRANSITION = "transition", "Transition Material"
        B_ROLL = "b_roll", "B-Roll"
        PICKUP = "pickup", "Pickup"
        ALTERNATE_TAKE = "alternate_take", "Alternate Take"
        EFFECTS_PLATE = "effects_plate", "VFX Plate"
        CLEAN_PLATE = "clean_plate", "Clean Plate"

    coverage_plan = models.ForeignKey(
        CoveragePlan,
        related_name="shots",
        on_delete=models.CASCADE,
    )
    shot_code = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    shot_category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.MEDIUM,
    )
    editorial_purpose = models.TextField(blank=True)
    framing_notes = models.TextField(blank=True)
    camera_movement = models.CharField(max_length=100, blank=True)
    lens_notes = models.CharField(max_length=100, blank=True)
    duration_target_seconds = models.PositiveIntegerField(default=5)
    sequence_order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    character = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        related_name="shots",
        on_delete=models.SET_NULL,
    )
    created_by = models.ForeignKey(
        "projects.Membership",
        related_name="created_shots",
        on_delete=models.PROTECT,
    )

    class Meta:
        unique_together = ("coverage_plan", "shot_code")
        ordering = ("sequence_order", "shot_code")

    def __str__(self):
        return f"Shot {self.shot_code}: {self.title} ({self.shot_category})"


class ShotTaskLink(models.Model):
    shot = models.ForeignKey(
        ShotDefinition,
        related_name="task_links",
        on_delete=models.CASCADE,
    )
    task = models.ForeignKey(
        ProductionTask,
        related_name="shot_links",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("shot", "task")

    def clean(self):
        if self.shot.coverage_plan.project_id != self.task.project_id:
            raise ValidationError("Shot and Task must belong to the same project.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class EditorialWarningWaiver(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        related_name="editorial_waivers",
        on_delete=models.CASCADE,
    )
    coverage_plan = models.ForeignKey(
        CoveragePlan,
        related_name="warning_waivers",
        on_delete=models.CASCADE,
    )
    warning_code = models.CharField(max_length=80)
    reason = models.TextField()
    waived_by = models.ForeignKey(
        "projects.Membership",
        related_name="waived_editorial_warnings",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("coverage_plan", "warning_code")

    def __str__(self):
        return f"Waiver [{self.warning_code}] by {self.waived_by.credited_name}"
