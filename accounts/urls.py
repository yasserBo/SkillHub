from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path(
        "register/",
        views.learner_register,
        name="learner_register",
    ),
    path(
        "register/instructor/",
        views.instructor_register,
        name="instructor_register",
    ),
    path(
        "login/",
        views.RoleBasedLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "dashboard/",
        views.dashboard_redirect,
        name="dashboard",
    ),
    path(
        "dashboard/learner/",
        views.learner_dashboard,
        name="learner_dashboard",
    ),
    path(
        "dashboard/instructor/",
        views.instructor_dashboard,
        name="instructor_dashboard",
    ),
    path(
    "profile/",
    views.learner_profile,
    name="learner_profile",
    ),
    path(
        "profile/edit/",
        views.learner_profile_update,
        name="learner_profile_update",
    ),
]