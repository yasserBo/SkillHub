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
        auth_views.LoginView.as_view(
            template_name="accounts/login.html"
        ),
        name="login",
    ),
]