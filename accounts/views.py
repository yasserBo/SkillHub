from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import (
    InstructorRegistrationForm,
    LearnerProfileUpdateForm,
    LearnerRegistrationForm,
    SkillHubAuthenticationForm,
)
from .models import LearnerProfile,User



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

@login_required
def learner_profile(request):
    """Display the logged-in learner's profile."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    profile, _ = LearnerProfile.objects.get_or_create(
        user=request.user,
    )

    return render(
        request,
        "accounts/learner_profile.html",
        {
            "profile": profile,
        },
    )


@login_required
def learner_profile_update(request):
    """Allow a learner to update their own profile."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    profile, _ = LearnerProfile.objects.get_or_create(
        user=request.user,
    )

    if request.method == "POST":
        form = LearnerProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=request.user,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your profile was updated successfully.",
            )

            return redirect("accounts:learner_profile")
    else:
        form = LearnerProfileUpdateForm(
            instance=profile,
            user=request.user,
        )

    return render(
        request,
        "accounts/learner_profile_update.html",
        {
            "form": form,
            "profile": profile,
        },
    )