from django.contrib import admin

from .models import (
    CanonicalSelection,
    DepartmentReview,
    DirectorReview,
    Submission,
    SubmissionAttestation,
    SubmissionVersion,
)

admin.site.register(Submission)
admin.site.register(SubmissionVersion)
admin.site.register(SubmissionAttestation)
admin.site.register(DepartmentReview)
admin.site.register(DirectorReview)
admin.site.register(CanonicalSelection)
