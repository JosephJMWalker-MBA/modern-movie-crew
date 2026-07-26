from django.db import models


class Character(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        related_name="characters",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=160)
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "name")

    def __str__(self):
        return f"{self.name} ({self.project.name})"


class CharacterIdentityVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        SUPERSEDED = "superseded", "Superseded"

    character = models.ForeignKey(
        Character,
        related_name="identity_versions",
        on_delete=models.CASCADE,
    )
    version_number = models.PositiveIntegerField()
    facial_structure_notes = models.TextField(blank=True)
    body_type = models.CharField(max_length=160, blank=True)
    canonical_reference_image = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    approved_by = models.ForeignKey(
        "projects.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("character", "version_number")
        ordering = ("-version_number",)

    def __str__(self):
        return f"{self.character.name} Identity v{self.version_number} [{self.status}]"


class CharacterReferenceAsset(models.Model):
    class AssetType(models.TextChoices):
        TURNAROUND = "turnaround", "Turnaround Sheet"
        MODEL_CONFIG = "model_config", "Model Config"
        KEYFRAME = "keyframe", "Reference Keyframe"
        EXPRESSION = "expression", "Expression Sheet"

    character_identity_version = models.ForeignKey(
        CharacterIdentityVersion,
        related_name="reference_assets",
        on_delete=models.CASCADE,
    )
    asset_type = models.CharField(max_length=30, choices=AssetType.choices)
    title = models.CharField(max_length=200)
    storage_key = models.CharField(max_length=500)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.asset_type})"


class CharacterLook(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"

    character = models.ForeignKey(
        Character,
        related_name="looks",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=160)
    wardrobe_description = models.TextField(blank=True)
    costume_reference_images = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        "projects.Membership",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character.name} - Look: {self.name}"


class VoiceProfile(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"

    character = models.ForeignKey(
        Character,
        related_name="voice_profiles",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=160)
    voice_actor_name = models.CharField(max_length=160, blank=True)
    model_settings = models.JSONField(default=dict, blank=True)
    sample_audio_key = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        "projects.Membership",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character.name} - Voice: {self.name}"


class PerformanceProfile(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"

    character = models.ForeignKey(
        Character,
        related_name="performance_profiles",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=160)
    emotional_range = models.TextField(blank=True)
    movement_notes = models.TextField(blank=True)
    mocap_reference_key = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        "projects.Membership",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character.name} - Performance: {self.name}"


class CharacterSceneState(models.Model):
    character = models.ForeignKey(
        Character,
        related_name="scene_states",
        on_delete=models.CASCADE,
    )
    scene = models.ForeignKey(
        "production.Scene",
        related_name="character_states",
        on_delete=models.CASCADE,
    )
    injury_notes = models.TextField(blank=True)
    dirt_blood_level = models.CharField(max_length=100, blank=True)
    wardrobe_damage = models.TextField(blank=True)
    emotional_state = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        "projects.Membership",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("character", "scene")

    def __str__(self):
        return f"{self.character.name} State in Scene {self.scene.scene_number}"


class CharacterRightsRecord(models.Model):
    character = models.ForeignKey(
        Character,
        related_name="rights_records",
        on_delete=models.CASCADE,
    )
    licensor_name = models.CharField(max_length=200)
    actor_membership = models.ForeignKey(
        "projects.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    likeness_authorized = models.BooleanField(default=True)
    voice_authorized = models.BooleanField(default=True)
    model_training_allowed = models.BooleanField(default=False)
    commercial_use_allowed = models.BooleanField(default=True)
    effective_date = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateTimeField(null=True, blank=True)
    document_key = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"Rights record for {self.character.name} ({self.licensor_name})"
