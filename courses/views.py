from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from .forms import (
    CourseCreationForm,
    CourseReviewForm,
    CourseSectionForm,
    QuizForm,
    QuizQuestionForm,
    VideoLessonUploadForm,
)

from .models import (
    Category,
    Course,
    CourseReview,
    CourseSection,
    Enrollment,
    PaymentTransaction,
    Quiz,
    QuizQuestion,
    VideoLesson,
)

from django.db import transaction
from django.utils import timezone
from django.db.models import Avg



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
    """Display, search, and filter approved SkillHub courses."""

    query = request.GET.get("q", "").strip()
    category_value = request.GET.get("category", "").strip()
    selected_level = request.GET.get("level", "").strip()

    selected_category_id = None

    approved_courses = (
        Course.objects
        .filter(status=Course.Status.APPROVED)
        .select_related("category", "instructor")
    )

    # Keyword search
    if query:
        approved_courses = approved_courses.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(instructor__first_name__icontains=query)
            | Q(instructor__last_name__icontains=query)
            | Q(instructor__email__icontains=query)
        )

    # Category filter
    if category_value.isdigit():
        selected_category_id = int(category_value)

        approved_courses = approved_courses.filter(
            category_id=selected_category_id
        )

    # Level filter
    valid_levels = {
        value
        for value, label in Course.Level.choices
    }

    if selected_level in valid_levels:
        approved_courses = approved_courses.filter(
            level=selected_level
        )
    else:
        selected_level = ""

    approved_courses = approved_courses.order_by(
        "-created_at"
    )

    # Only categories containing approved courses
    categories = (
        Category.objects
        .filter(
            courses__status=Course.Status.APPROVED
        )
        .distinct()
        .order_by("name")
    )

    category_options = [
        {
            "id": category.pk,
            "name": category.name,
            "selected": category.pk == selected_category_id,
        }
        for category in categories
    ]

    level_options = [
        {
            "value": value,
            "label": label,
            "selected": value == selected_level,
        }
        for value, label in Course.Level.choices
    ]

    paginator = Paginator(
        approved_courses,
        9,
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Keep search and filters when moving between pages
    pagination_parameters = request.GET.copy()
    pagination_parameters.pop("page", None)

    pagination_query = (
        pagination_parameters.urlencode()
    )

    return render(
        request,
        "courses/course_catalog.html",
        {
            "page_obj": page_obj,
            "categories": category_options,
            "level_choices": level_options,
            "query": query,
            "selected_category_id": selected_category_id,
            "selected_level": selected_level,
            "result_count": paginator.count,
            "pagination_query": pagination_query,
        },
    )

    






def course_detail(request, course_id):
    """Display an approved course and its reviews."""

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

    reviews = (
        CourseReview.objects
        .filter(course=course)
        .select_related("learner")
    )

    average_rating = reviews.aggregate(
        average=Avg("rating")
    )["average"]

    is_enrolled = False
    current_review = None

    if (
        request.user.is_authenticated
        and request.user.role == User.Role.LEARNER
    ):
        is_enrolled = Enrollment.objects.filter(
            learner=request.user,
            course=course,
        ).exists()

        current_review = CourseReview.objects.filter(
            learner=request.user,
            course=course,
        ).first()

    review_form = CourseReviewForm(
        instance=current_review
    )

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "learning_objectives": learning_objectives,
            "is_enrolled": is_enrolled,
            "reviews": reviews,
            "review_count": reviews.count(),
            "average_rating": average_rating,
            "current_review": current_review,
            "review_form": review_form,
        },
    )

@login_required
@require_POST
def course_enroll(request, course_id):
    """Allow a learner to enroll in an approved course."""

    if request.user.role != User.Role.LEARNER:
        messages.warning(
            request,
            "Only learner accounts can enroll in courses.",
        )

        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        status=Course.Status.APPROVED,
        price=0,
    )

    enrollment, created = Enrollment.objects.get_or_create(
        learner=request.user,
        course=course,
    )

    if created:
        messages.success(
            request,
            f"You successfully enrolled in {course.title}.",
        )
    else:
        messages.info(
            request,
            "You are already enrolled in this course.",
        )

    return redirect(
        "courses:course_detail",
        course_id=course.pk,
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

@login_required
def course_purchase(request, course_id):
    """Simulate payment and enroll a learner in a paid course."""

    if request.user.role != User.Role.LEARNER:
        messages.warning(
            request,
            "Only learner accounts can purchase courses.",
        )

        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course.objects.select_related(
            "category",
            "instructor",
        ),
        pk=course_id,
        status=Course.Status.APPROVED,
        price__gt=0,
    )

    if Enrollment.objects.filter(
        learner=request.user,
        course=course,
    ).exists():
        messages.info(
            request,
            "You are already enrolled in this course.",
        )

        return redirect(
            "courses:course_detail",
            course_id=course.pk,
        )

    if request.method == "POST":
        with transaction.atomic():
            existing_payment = PaymentTransaction.objects.filter(
                learner=request.user,
                course=course,
                status=PaymentTransaction.Status.SUCCESSFUL,
            ).first()

            if existing_payment is None:
                PaymentTransaction.objects.create(
                    learner=request.user,
                    course=course,
                    amount=course.price,
                    status=PaymentTransaction.Status.SUCCESSFUL,
                    completed_at=timezone.now(),
                )

            Enrollment.objects.get_or_create(
                learner=request.user,
                course=course,
            )

        messages.success(
            request,
            (
                "Payment completed successfully. "
                "You are now enrolled in the course."
            ),
        )

        return redirect(
            "courses:course_detail",
            course_id=course.pk,
        )

    return render(
        request,
        "courses/course_purchase.html",
        {
            "course": course,
        },
    )

@login_required
def learner_course_content(request, course_id):
    """Display lessons and published quizzes to an enrolled learner."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    enrollment = get_object_or_404(
        Enrollment.objects.select_related(
            "course",
            "course__category",
            "course__instructor",
        ),
        learner=request.user,
        course_id=course_id,
        course__status=Course.Status.APPROVED,
    )

    course = enrollment.course

    sections = (
        course.sections
        .prefetch_related("lessons")
        .order_by("order", "pk")
    )

    published_quizzes = (
        course.quizzes
        .filter(is_published=True)
        .prefetch_related("questions")
        .order_by("-created_at")
    )

    return render(
        request,
        "courses/learner_course_content.html",
        {
            "course": course,
            "enrollment": enrollment,
            "sections": sections,
            "published_quizzes": published_quizzes,
        },
    )


@login_required
def lesson_watch(request, lesson_id):
    """Allow an enrolled learner to watch a video lesson."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    lesson = get_object_or_404(
        VideoLesson.objects.select_related(
            "section",
            "section__course",
        ),
        pk=lesson_id,
        section__course__status=Course.Status.APPROVED,
        section__course__enrollments__learner=request.user,
    )

    course = lesson.section.course

    lessons = list(
        VideoLesson.objects.filter(
            section__course=course,
        )
        .select_related("section")
        .order_by(
            "section__order",
            "order",
            "pk",
        )
    )

    current_index = next(
        (
            index
            for index, current_lesson in enumerate(lessons)
            if current_lesson.pk == lesson.pk
        ),
        None,
    )

    previous_lesson = None
    next_lesson = None

    if current_index is not None:
        if current_index > 0:
            previous_lesson = lessons[current_index - 1]

        if current_index < len(lessons) - 1:
            next_lesson = lessons[current_index + 1]

    return render(
        request,
        "courses/lesson_watch.html",
        {
            "course": course,
            "lesson": lesson,
            "previous_lesson": previous_lesson,
            "next_lesson": next_lesson,
        },
    )

@login_required
@require_POST
def course_review_submit(request, course_id):
    """Create or update an enrolled learner's review."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        status=Course.Status.APPROVED,
        enrollments__learner=request.user,
    )

    existing_review = CourseReview.objects.filter(
        learner=request.user,
        course=course,
    ).first()

    form = CourseReviewForm(
        request.POST,
        instance=existing_review,
    )

    if form.is_valid():
        review = form.save(commit=False)
        review.learner = request.user
        review.course = course
        review.save()

        messages.success(
            request,
            "Your course review was saved successfully.",
        )
    else:
        messages.error(
            request,
            "Please provide a valid rating.",
        )

    return redirect(
        "courses:course_detail",
        course_id=course.pk,
    )

@login_required
def instructor_quiz_list(request, course_id):
    """Display quizzes belonging to the instructor's course."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course.objects.prefetch_related(
            "quizzes__questions"
        ),
        pk=course_id,
        instructor=request.user,
    )

    return render(
        request,
        "courses/instructor_quiz_list.html",
        {
            "course": course,
        },
    )


@login_required
def quiz_create(request, course_id):
    """Allow a course owner to create a quiz."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        instructor=request.user,
    )

    if request.method == "POST":
        form = QuizForm(request.POST)

        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.course = course
            quiz.is_published = False
            quiz.save()

            messages.success(
                request,
                "The quiz was created successfully.",
            )

            return redirect(
                "courses:instructor_quiz_list",
                course_id=course.pk,
            )
    else:
        form = QuizForm()

    return render(
        request,
        "courses/quiz_form.html",
        {
            "course": course,
            "form": form,
        },
    )


@login_required
def quiz_question_create(request, course_id, quiz_id):
    """Allow the course owner to add a quiz question."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        instructor=request.user,
    )

    quiz = get_object_or_404(
        Quiz,
        pk=quiz_id,
        course=course,
    )

    if quiz.is_published:
        messages.warning(
            request,
            "Unpublish the quiz before adding more questions.",
        )

        return redirect(
            "courses:instructor_quiz_list",
            course_id=course.pk,
        )

    if request.method == "POST":
        form = QuizQuestionForm(
            request.POST,
            quiz=quiz,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "The question was added successfully.",
            )

            return redirect(
                "courses:instructor_quiz_list",
                course_id=course.pk,
            )
    else:
        next_order = quiz.questions.count() + 1

        form = QuizQuestionForm(
            quiz=quiz,
            initial={
                "order": next_order,
            },
        )

    return render(
        request,
        "courses/quiz_question_form.html",
        {
            "course": course,
            "quiz": quiz,
            "form": form,
        },
    )


@login_required
@require_POST
def quiz_publish(request, course_id, quiz_id):
    """Publish a quiz when it contains at least one question."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course,
        pk=course_id,
        instructor=request.user,
    )

    quiz = get_object_or_404(
        Quiz,
        pk=quiz_id,
        course=course,
    )

    if not quiz.questions.exists():
        messages.warning(
            request,
            "Add at least one question before publishing the quiz.",
        )

        return redirect(
            "courses:instructor_quiz_list",
            course_id=course.pk,
        )

    quiz.is_published = True
    quiz.save(
        update_fields=[
            "is_published",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "The quiz was published successfully.",
    )

    return redirect(
        "courses:instructor_quiz_list",
        course_id=course.pk,
    )