from django.contrib import admin

from .models import (
    Act,
    CharacterTaskLink,
    PacketSection,
    ProductionTask,
    Resource,
    Scene,
    Sequence,
    TaskClaim,
    TaskResource,
)

admin.site.register(Act)
admin.site.register(Sequence)
admin.site.register(Scene)
admin.site.register(ProductionTask)
admin.site.register(PacketSection)
admin.site.register(Resource)
admin.site.register(TaskResource)
admin.site.register(TaskClaim)
admin.site.register(CharacterTaskLink)
