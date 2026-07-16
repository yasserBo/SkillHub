from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import (
    InstructorRegistrationForm,
    LearnerRegistrationForm,
    SkillHubAuthenticationForm,
)
from .models import User


def learner_register(request):
    """Register a new learner account."""

    # Normal authenticated users should not create another account.
    # Staff users may access the page for testing and administration.
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = LearnerRegistrationForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "The learner account was created successfully.",
            )

            # Keep administrators on the registration page for testing.
            if request.user.is_authenticated and request.user.is_staff:
                return redirect("accounts:learner_register")

            return redirect("accounts:login")
    else:
        form = LearnerRegistrationForm()

    return render(
        request,
        "accounts/learner_register.html",
        {"form": form},
    )


def instructor_register(request):
    """Register a new instructor account."""

    if request.user.is_authenticated and not request.user.is_staff:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = InstructorRegistrationForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "The instructor account was created successfully.",
            )

            if request.user.is_authenticated and request.user.is_staff:
                return redirect("accounts:instructor_register")

            return redirect("accounts:login")
    else:
        form = InstructorRegistrationForm()

    return render(
        request,
        "accounts/instructor_register.html",
        {"form": form},
    )


class RoleBasedLoginView(LoginView):
    """Authenticate users and redirect them according to their role."""

    template_name = "accounts/login.html"
    authentication_form = SkillHubAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Preserve a safe `next` destination when one was supplied.
        next_url = self.get_redirect_url()

        if next_url:
            return next_url

        user = self.request.user

        if (
            user.is_superuser
            or user.is_staff
            or user.role == User.Role.ADMIN
        ):
            return reverse("admin:index")

        if user.role == User.Role.INSTRUCTOR:
            return reverse("accounts:instructor_dashboard")

        return reverse("accounts:learner_dashboard")


@login_required
def dashboard_redirect(request):
    """Send the authenticated user to the correct dashboard."""

    user = request.user

    if (
        user.is_superuser
        or user.is_staff
        or user.role == User.Role.ADMIN
    ):
        return redirect("admin:index")

    if user.role == User.Role.INSTRUCTOR:
        return redirect("accounts:instructor_dashboard")

    return redirect("accounts:learner_dashboard")


@login_required
def learner_dashboard(request):
    """Display the learner dashboard."""

    user = request.user

    if (
        user.is_superuser
        or user.is_staff
        or user.role == User.Role.ADMIN
    ):
        return redirect("admin:index")

    if user.role == User.Role.INSTRUCTOR:
        return redirect("accounts:instructor_dashboard")

    return render(
        request,
        "accounts/learner_dashboard.html",
    )


@login_required
def instructor_dashboard(request):
    """Display the instructor dashboard."""

    user = request.user

    if (
        user.is_superuser
        or user.is_staff
        or user.role == User.Role.ADMIN
    ):
        return redirect("admin:index")

    if user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:learner_dashboard")

    return render(
        request,
        "accounts/instructor_dashboard.html",
    )