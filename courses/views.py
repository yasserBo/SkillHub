from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .forms import CourseCreationForm
from .models import Course


@login_required
def instructor_course_list(request):
    """Display courses belonging to the logged-in instructor."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    courses = (
        Course.objects
        .filter(instructor=request.user)
        .select_related("category")
    )

    return render(
        request,
        "courses/instructor_course_list.html",
        {
            "courses": courses,
        },
    )


@login_required
def course_create(request):
    """Allow an instructor to create a draft course."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = CourseCreationForm(request.POST)

        if form.is_valid():
            course = form.save(commit=False)

            course.instructor = request.user
            course.status = Course.Status.DRAFT
            course.save()

            messages.success(
                request,
                "Your course was created and saved as a draft.",
            )

            return redirect(
                "courses:instructor_course_list"
            )
    else:
        form = CourseCreationForm()

    return render(
        request,
        "courses/course_create.html",
        {
            "form": form,
        },
    )

@login_required
@require_POST
def course_submit(request, course_id):
    """Submit an instructor's course for administrator review."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        instructor=request.user,
    )

    allowed_statuses = {
        Course.Status.DRAFT,
        Course.Status.REJECTED,
    }

    if course.status not in allowed_statuses:
        messages.warning(
            request,
            "This course has already been submitted or approved.",
        )

        return redirect(
            "courses:instructor_course_list"
        )

    course.status = Course.Status.SUBMITTED
    course.rejection_reason = ""

    course.save(
        update_fields=[
            "status",
            "rejection_reason",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Your course was submitted for administrator review.",
    )

    return redirect(
        "courses:instructor_course_list"
    )

def course_catalog(request):
    """Display approved SkillHub courses."""

    approved_courses = (
        Course.objects
        .filter(status=Course.Status.APPROVED)
        .select_related("category", "instructor")
        .order_by("-created_at")
    )

    paginator = Paginator(
        approved_courses,
        9,
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "courses/course_catalog.html",
        {
            "page_obj": page_obj,
        },
    )