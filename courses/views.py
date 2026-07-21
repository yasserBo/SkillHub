from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q

from .forms import (
    CourseCreationForm,
    CourseSectionForm,
    VideoLessonUploadForm,
)
from .models import Course, CourseSection

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
    """Display and search approved SkillHub courses."""

    query = request.GET.get("q", "").strip()

    approved_courses = (
        Course.objects
        .filter(status=Course.Status.APPROVED)
        .select_related("category", "instructor")
    )

    if query:
        approved_courses = approved_courses.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(instructor__first_name__icontains=query)
            | Q(instructor__last_name__icontains=query)
            | Q(instructor__email__icontains=query)
        )

    approved_courses = approved_courses.order_by(
        "-created_at"
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
            "query": query,
            "result_count": paginator.count,
        },
    )





def course_detail(request, course_id):
    """Display the full details of an approved course."""

    course = get_object_or_404(
        Course.objects.select_related(
            "category",
            "instructor",
        ),
        pk=course_id,
        status=Course.Status.APPROVED,
    )

    learning_objectives = [
        objective.strip()
        for objective in course.learning_objectives.splitlines()
        if objective.strip()
    ]

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "learning_objectives": learning_objectives,
        },
    )

@login_required
def course_content_manage(request, course_id):
    """Display and organize the instructor's course content."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course.objects.prefetch_related(
            "sections__lessons"
        ),
        pk=course_id,
        instructor=request.user,
    )

    content_editable = course.status in {
        Course.Status.DRAFT,
        Course.Status.REJECTED,
    }

    return render(
        request,
        "courses/course_content_manage.html",
        {
            "course": course,
            "content_editable": content_editable,
        },
    )


@login_required
def course_section_create(request, course_id):
    """Allow the course owner to create a content section."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        instructor=request.user,
    )

    if course.status not in {
        Course.Status.DRAFT,
        Course.Status.REJECTED,
    }:
        messages.warning(
            request,
            (
                "Content cannot be changed while the course "
                "is submitted or approved."
            ),
        )

        return redirect(
            "courses:course_content_manage",
            course_id=course.pk,
        )

    if request.method == "POST":
        form = CourseSectionForm(
            request.POST,
            course=course,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "The course section was created successfully.",
            )

            return redirect(
                "courses:course_content_manage",
                course_id=course.pk,
            )
    else:
        form = CourseSectionForm(
            course=course,
        )

    return render(
        request,
        "courses/course_section_create.html",
        {
            "course": course,
            "form": form,
        },
    )


@login_required
def video_lesson_upload(request, course_id):
    """Allow the course owner to upload a video lesson."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        instructor=request.user,
    )

    if course.status not in {
        Course.Status.DRAFT,
        Course.Status.REJECTED,
    }:
        messages.warning(
            request,
            (
                "Videos cannot be uploaded while the course "
                "is submitted or approved."
            ),
        )

        return redirect(
            "courses:course_content_manage",
            course_id=course.pk,
        )

    if not CourseSection.objects.filter(
        course=course
    ).exists():
        messages.warning(
            request,
            "Create a course section before uploading a lesson.",
        )

        return redirect(
            "courses:course_section_create",
            course_id=course.pk,
        )

    if request.method == "POST":
        form = VideoLessonUploadForm(
            request.POST,
            request.FILES,
            course=course,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "The video lesson was uploaded successfully.",
            )

            return redirect(
                "courses:course_content_manage",
                course_id=course.pk,
            )
    else:
        form = VideoLessonUploadForm(
            course=course,
        )

    return render(
        request,
        "courses/video_lesson_upload.html",
        {
            "course": course,
            "form": form,
        },
    )