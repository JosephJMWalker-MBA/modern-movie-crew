from django.contrib import admin

from .models import (
    Character,
    CharacterIdentityVersion,
    CharacterLook,
    CharacterReferenceAsset,
    CharacterRightsRecord,
    CharacterSceneState,
    PerformanceProfile,
    VoiceProfile,
)

admin.site.register(Character)
admin.site.register(CharacterIdentityVersion)
admin.site.register(CharacterReferenceAsset)
admin.site.register(CharacterLook)
admin.site.register(VoiceProfile)
admin.site.register(PerformanceProfile)
admin.site.register(CharacterSceneState)
admin.site.register(CharacterRightsRecord)
