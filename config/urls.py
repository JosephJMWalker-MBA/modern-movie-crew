from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from apps.characters import views as char_views
from apps.core import views as core_views
from apps.credits import views as credit_views
from apps.production import views as prod_views
from apps.projects import views as proj_views
from apps.submissions import views as sub_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Core, Auth & Notifications
    path("", core_views.dashboard_view, name="dashboard"),
    path("register/", core_views.register_view, name="register"),
    path("notifications/", core_views.notifications_view, name="notifications"),
    path("notifications/<int:notif_id>/read/", core_views.mark_notification_read_view, name="mark_notification_read"),
    # Projects & Room
    path("projects/new/", proj_views.create_project_view, name="create_project"),
    path("projects/<slug:slug>/", proj_views.project_detail_view, name="project_detail"),
    path("projects/<slug:slug>/room/", proj_views.production_room_view, name="production_room"),
    path("projects/<slug:slug>/crew/add/", proj_views.add_crew_member_view, name="add_crew_member"),
    path("projects/<slug:slug>/profile/edit/", proj_views.edit_profile_view, name="edit_profile"),
    path("projects/<slug:slug>/invites/new/", proj_views.create_invite_view, name="create_invite"),
    path("projects/<slug:slug>/invites/<int:invite_id>/revoke/", proj_views.revoke_invite_view, name="revoke_invite"),
    path("invites/<str:token_str>/accept/", proj_views.accept_invite_view, name="accept_invite"),
    path("projects/<slug:slug>/spare-gen/", proj_views.spare_gen_view, name="spare_gen"),
    path("projects/<slug:slug>/activity/", core_views.activity_feed_view, name="activity_feed"),
    # Characters
    path("projects/<slug:slug>/characters/", char_views.character_list_view, name="character_list"),
    path("projects/<slug:slug>/characters/new/", char_views.create_character_view, name="create_character"),
    path("projects/<slug:slug>/characters/<int:identity_id>/approve/", char_views.approve_identity_view, name="approve_character_identity"),
    # Production Board & Tasks
    path("projects/<slug:slug>/board/", prod_views.project_board_view, name="project_board"),
    path("projects/<slug:slug>/tasks/new/", prod_views.create_task_view, name="create_task"),
    path("projects/<slug:slug>/tasks/<int:task_id>/", prod_views.task_detail_view, name="task_detail"),
    path("projects/<slug:slug>/sections/<int:section_id>/approve/", prod_views.approve_section_view, name="approve_packet_section"),
    path("projects/<slug:slug>/tasks/<int:task_id>/open/", prod_views.open_task_view, name="open_task"),
    path("projects/<slug:slug>/tasks/<int:task_id>/claim/", prod_views.claim_task_view, name="claim_task"),
    # Submissions & Reviews
    path("projects/<slug:slug>/tasks/<int:task_id>/upload/", sub_views.upload_v1_view, name="upload_v1"),
    path("projects/<slug:slug>/versions/<int:version_id>/dept-review/", sub_views.department_review_view, name="department_review"),
    path("projects/<slug:slug>/versions/<int:version_id>/revision/", sub_views.director_revision_view, name="director_revision"),
    path("projects/<slug:slug>/submissions/<int:submission_id>/upload-v2/", sub_views.upload_v2_view, name="upload_v2"),
    path("projects/<slug:slug>/versions/<int:version_id>/accept/", sub_views.director_accept_view, name="director_accept"),
    # Credits & Ledger
    path("projects/<slug:slug>/credits/", credit_views.credit_ledger_view, name="credit_ledger"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
