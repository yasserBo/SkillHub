from django.urls import path

from . import views


app_name = "courses"

urlpatterns = [
    path(
        "",
        views.course_catalog,
        name="course_catalog",
    ),
    path(
        "learning/<int:course_id>/",
        views.learner_course_content,
        name="learner_course_content",
    ),
    path(
        "learning/lessons/<int:lesson_id>/",
        views.lesson_watch,
        name="lesson_watch",
    ),
    path(
        "<int:course_id>/",
        views.course_detail,
        name="course_detail",
    ),
    path(
        "<int:course_id>/enroll/",
        views.course_enroll,
        name="course_enroll",
    ),
    path(
        "<int:course_id>/purchase/",
        views.course_purchase,
        name="course_purchase",
    ),
    path(
        "instructor/",
        views.instructor_course_list,
        name="instructor_course_list",
    ),
    path(
        "instructor/create/",
        views.course_create,
        name="course_create",
    ),
    path(
        "instructor/<int:course_id>/content/",
        views.course_content_manage,
        name="course_content_manage",
    ),
    path(
        "instructor/<int:course_id>/content/sections/add/",
        views.course_section_create,
        name="course_section_create",
    ),
    path(
        "instructor/<int:course_id>/content/videos/upload/",
        views.video_lesson_upload,
        name="video_lesson_upload",
    ),
    path(
        "instructor/<int:course_id>/submit/",
        views.course_submit,
        name="course_submit",
    ),
]