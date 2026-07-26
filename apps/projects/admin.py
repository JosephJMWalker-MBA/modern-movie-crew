from django.contrib import admin

from .models import (
    Department,
    Membership,
    MembershipAgreement,
    ProductionRole,
    Project,
    ProjectTermsVersion,
    RoleAssignment,
)

admin.site.register(Project)
admin.site.register(ProjectTermsVersion)
admin.site.register(Department)
admin.site.register(Membership)
admin.site.register(MembershipAgreement)
admin.site.register(ProductionRole)
admin.site.register(RoleAssignment)
