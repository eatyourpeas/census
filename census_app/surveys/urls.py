from django.urls import path
from . import views

app_name = "surveys"

urlpatterns = [
    path("", views.survey_list, name="list"),
    # User management hub (must be before slug routes)
    path("manage/users/", views.user_management_hub, name="user_management_hub"),
    path("<slug:slug>/bulk-upload/", views.bulk_upload, name="bulk_upload"),
    path("create/", views.survey_create, name="create"),
    # Repeats (collections) integrated with groups
    path("<slug:slug>/groups/repeat/create", views.survey_groups_repeat_create, name="survey_groups_repeat_create"),
    path("<slug:slug>/groups/<int:gid>/repeat/remove", views.survey_group_repeat_remove, name="survey_group_repeat_remove"),
    path("<slug:slug>/groups/template/create", views.survey_group_create_from_template, name="groups_create_from_template"),
    path("<slug:slug>/preview/", views.survey_preview, name="preview"),
    # Participant routes
    path("<slug:slug>/take/", views.survey_take, name="take"),
    path("<slug:slug>/take/unlisted/<str:key>/", views.survey_take_unlisted, name="take_unlisted"),
    path("<slug:slug>/take/token/<str:token>/", views.survey_take_token, name="take_token"),
    path("<slug:slug>/thank-you/", views.survey_thank_you, name="thank_you"),
    path("<slug:slug>/", views.survey_detail, name="detail"),
    path("<slug:slug>/dashboard/", views.survey_dashboard, name="dashboard"),
    path("<slug:slug>/dashboard/publish", views.survey_publish_update, name="publish_update"),
    path("<slug:slug>/tokens/", views.survey_tokens, name="tokens"),
    path("<slug:slug>/tokens/export.csv", views.survey_tokens_export_csv, name="tokens_export_csv"),
    path("<slug:slug>/style/update", views.survey_style_update, name="style_update"),
    path("<slug:slug>/groups/", views.survey_groups, name="groups"),
    path("<slug:slug>/groups/reorder", views.survey_groups_reorder, name="survey_groups_reorder"),
    path("<slug:slug>/groups/create", views.survey_group_create, name="survey_group_create"),
    path("<slug:slug>/groups/<int:gid>/edit", views.survey_group_edit, name="survey_group_edit"),
    path("<slug:slug>/groups/<int:gid>/delete", views.survey_group_delete, name="survey_group_delete"),
    path("<slug:slug>/unlock/", views.survey_unlock, name="unlock"),
    path("<slug:slug>/export.csv", views.survey_export_csv, name="export_csv"),
    # Group question management (per-group)
    path("<slug:slug>/builder/groups/<int:gid>/", views.group_builder, name="group_builder"),
    path("<slug:slug>/builder/questions/create", views.builder_question_create, name="builder_question_create"),
    path("<slug:slug>/builder/groups/<int:gid>/questions/create", views.builder_group_question_create, name="builder_group_question_create"),
    path("<slug:slug>/builder/questions/<int:qid>/edit", views.builder_question_edit, name="builder_question_edit"),
    path("<slug:slug>/builder/groups/<int:gid>/questions/<int:qid>/edit", views.builder_group_question_edit, name="builder_group_question_edit"),
    path("<slug:slug>/builder/questions/<int:qid>/delete", views.builder_question_delete, name="builder_question_delete"),
    path("<slug:slug>/builder/groups/<int:gid>/questions/<int:qid>/delete", views.builder_group_question_delete, name="builder_group_question_delete"),
    path("<slug:slug>/builder/questions/reorder", views.builder_questions_reorder, name="builder_questions_reorder"),
    path("<slug:slug>/builder/groups/<int:gid>/questions/reorder", views.builder_group_questions_reorder, name="builder_group_questions_reorder"),
    path("<slug:slug>/builder/groups/create", views.builder_group_create, name="builder_group_create"),
    path("<slug:slug>/builder/demographics/update", views.builder_demographics_update, name="builder_demographics_update"),
    path("<slug:slug>/builder/professional/update", views.builder_professional_update, name="builder_professional_update"),
    # User management portal
    path("org/<int:org_id>/users/", views.org_users, name="org_users"),
    path("<slug:slug>/users/", views.survey_users, name="survey_users"),
]
