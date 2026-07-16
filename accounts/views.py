from urllib import request

from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import (
    InstructorRegistrationForm,
    LearnerRegistrationForm,
)

def learner_register(request):
    """Register a new learner account."""

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
    """Register a new SkillHub instructor."""

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