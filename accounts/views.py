from urllib import request

from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import LearnerRegistrationForm


def learner_register(request):
    """Register a new learner account."""

    if request.user.is_authenticated:
        return redirect("accounts:login")

    if request.method == "POST":
        form = LearnerRegistrationForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your learner account was created successfully. "
                "You can now log in.",
            )

            return redirect("accounts:login")
    else:
        form = LearnerRegistrationForm()

    return render(
        request,
        "accounts/learner_register.html",
        {"form": form},
    )