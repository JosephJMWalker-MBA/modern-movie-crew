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

    def __str__(self):
        return f"{self.task.code} -> Character: {self.character.name}"
