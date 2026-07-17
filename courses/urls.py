from django.urls import path

from . import views


app_name = "courses"

urlpatterns = [
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
        "instructor/<int:course_id>/submit/",
        views.course_submit,
        name="course_submit",
    ),
]