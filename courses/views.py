from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
import uuid
import csv



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
    Certificate,
    Course,
    CourseReview,
    CourseSection,
    Enrollment,
    PaymentTransaction,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizQuestion,
    VideoLesson,
)

from django.db import transaction
from django.utils import timezone
from django.db.models import Avg, Count, DecimalField, Sum, Value
from django.utils.dateparse import parse_date
from io import BytesIO

from django.http import HttpResponse
from django.utils.text import slugify

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from decimal import Decimal

from django.db.models import (
    Count,
    DecimalField,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from collections import Counter

from django.db.models import Avg, Count


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


def _learner_has_completed_course(learner, course):
    """Return True when every published course quiz has been passed."""

    published_quiz_ids = set(
        Quiz.objects.filter(
            course=course,
            is_published=True,
        ).values_list(
            "pk",
            flat=True,
        )
    )

    if not published_quiz_ids:
        return False

    passed_quiz_ids = set(
        QuizAttempt.objects.filter(
            learner=learner,
            quiz_id__in=published_quiz_ids,
            passed=True,
        )
        .values_list(
            "quiz_id",
            flat=True,
        )
        .distinct()
    )

    return published_quiz_ids.issubset(
        passed_quiz_ids
    )

@login_required
def learner_course_content(request, course_id):
    """Display lessons, quizzes and certificate status."""

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

    published_quizzes = list(
        course.quizzes
        .filter(is_published=True)
        .prefetch_related("questions")
        .order_by("-created_at")
    )

    quiz_cards = []

    for quiz in published_quizzes:
        latest_attempt = (
            QuizAttempt.objects
            .filter(
                learner=request.user,
                quiz=quiz,
            )
            .order_by("-completed_at")
            .first()
        )

        quiz_cards.append(
            {
                "quiz": quiz,
                "latest_attempt": latest_attempt,
            }
        )

    published_quiz_ids = {
        quiz.pk
        for quiz in published_quizzes
    }

    passed_quiz_ids = set(
        QuizAttempt.objects.filter(
            learner=request.user,
            quiz_id__in=published_quiz_ids,
            passed=True,
        )
        .values_list(
            "quiz_id",
            flat=True,
        )
        .distinct()
    )

    published_quiz_count = len(
        published_quiz_ids
    )

    passed_quiz_count = len(
        passed_quiz_ids
    )

    certificate_eligible = (
        published_quiz_count > 0
        and published_quiz_ids.issubset(
            passed_quiz_ids
        )
    )

    certificate = Certificate.objects.filter(
        learner=request.user,
        course=course,
    ).first()

    return render(
        request,
        "courses/learner_course_content.html",
        {
            "course": course,
            "enrollment": enrollment,
            "sections": sections,
            "quiz_cards": quiz_cards,
            "published_quiz_count": published_quiz_count,
            "passed_quiz_count": passed_quiz_count,
            "certificate_eligible": certificate_eligible,
            "certificate": certificate,
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


def _build_quiz_question_rows(
    questions,
    selected_answers=None,
    errors=None,
):
    """Prepare quiz questions and answer choices for the template."""

    selected_answers = selected_answers or {}
    errors = errors or {}

    rows = []

    for question in questions:
        rows.append(
            {
                "question": question,
                "selected": selected_answers.get(
                    question.pk,
                    "",
                ),
                "error": errors.get(
                    question.pk,
                    "",
                ),
                "options": [
                    {
                        "value": "A",
                        "text": question.option_a,
                    },
                    {
                        "value": "B",
                        "text": question.option_b,
                    },
                    {
                        "value": "C",
                        "text": question.option_c,
                    },
                    {
                        "value": "D",
                        "text": question.option_d,
                    },
                ],
            }
        )

    return rows



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

@login_required
def quiz_take(request, quiz_id):
    """Allow an enrolled learner to complete a published quiz."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    quiz = get_object_or_404(
        Quiz.objects.select_related(
            "course",
            "course__category",
        ).prefetch_related(
            "questions",
        ),
        pk=quiz_id,
        is_published=True,
        course__status=Course.Status.APPROVED,
        course__enrollments__learner=request.user,
    )

    questions = list(
        quiz.questions.order_by(
            "order",
            "pk",
        )
    )

    if not questions:
        messages.warning(
            request,
            "This quiz does not contain any questions.",
        )

        return redirect(
            "courses:learner_course_content",
            course_id=quiz.course.pk,
        )

    selected_answers = {}
    errors = {}

    if request.method == "POST":
        valid_options = {
            value
            for value, _label
            in QuizQuestion.CorrectOption.choices
        }

        for question in questions:
            field_name = f"question_{question.pk}"

            selected_option = (
                request.POST
                .get(field_name, "")
                .strip()
                .upper()
            )

            selected_answers[question.pk] = selected_option

            if selected_option not in valid_options:
                errors[question.pk] = (
                    "Select one answer for this question."
                )

        if not errors:
            correct_count = sum(
                1
                for question in questions
                if selected_answers[question.pk]
                == question.correct_option
            )

            total_questions = len(questions)

            score = round(
                correct_count
                / total_questions
                * 100
            )

            passed = score >= quiz.passing_score

            with transaction.atomic():
                attempt = QuizAttempt.objects.create(
                    learner=request.user,
                    quiz=quiz,
                    score=score,
                    total_questions=total_questions,
                    correct_answers=correct_count,
                    passed=passed,
                )

                answers = [
                    QuizAnswer(
                        attempt=attempt,
                        question=question,
                        selected_option=selected_answers[
                            question.pk
                        ],
                        is_correct=(
                            selected_answers[question.pk]
                            == question.correct_option
                        ),
                    )
                    for question in questions
                ]

                QuizAnswer.objects.bulk_create(
                    answers
                )

            messages.success(
                request,
                "Your quiz was submitted successfully.",
            )

            return redirect(
                "courses:quiz_result",
                attempt_id=attempt.pk,
            )

    question_rows = _build_quiz_question_rows(
        questions=questions,
        selected_answers=selected_answers,
        errors=errors,
    )

    return render(
        request,
        "courses/quiz_take.html",
        {
            "quiz": quiz,
            "course": quiz.course,
            "question_rows": question_rows,
            "question_count": len(questions),
        },
    )

@login_required
def quiz_result(request, attempt_id):
    """Display the result of a learner's completed quiz attempt."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    attempt = get_object_or_404(
        QuizAttempt.objects.select_related(
            "quiz",
            "quiz__course",
        ),
        pk=attempt_id,
        learner=request.user,
        quiz__course__status=Course.Status.APPROVED,
        quiz__course__enrollments__learner=request.user,
    )

    answers = (
        QuizAnswer.objects
        .filter(attempt=attempt)
        .select_related("question")
        .order_by(
            "question__order",
            "question__pk",
        )
    )

    answer_rows = []

    for answer in answers:
        question = answer.question

        option_texts = {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d,
        }

        answer_rows.append(
            {
                "answer": answer,
                "question": question,
                "selected_text": option_texts.get(
                    answer.selected_option,
                    "",
                ),
                "correct_text": option_texts.get(
                    question.correct_option,
                    "",
                ),
            }
        )

    return render(
        request,
        "courses/quiz_result.html",
        {
            "attempt": attempt,
            "quiz": attempt.quiz,
            "course": attempt.quiz.course,
            "answer_rows": answer_rows,
        },
    )

@login_required
def certificate_download(request, course_id):
    """Generate and download a learner's course certificate."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course.objects.select_related(
            "category",
            "instructor",
        ),
        pk=course_id,
        status=Course.Status.APPROVED,
        enrollments__learner=request.user,
    )

    if not _learner_has_completed_course(
        request.user,
        course,
    ):
        messages.warning(
            request,
            (
                "You must pass every published quiz "
                "before downloading the certificate."
            ),
        )

        return redirect(
            "courses:learner_course_content",
            course_id=course.pk,
        )

    certificate, _created = (
        Certificate.objects.get_or_create(
            learner=request.user,
            course=course,
        )
    )

    learner_name = (
        request.user.get_full_name().strip()
        or request.user.email
    )

    instructor_name = (
        course.instructor.get_full_name().strip()
        or course.instructor.email
    )

    issue_date = timezone.localtime(
        certificate.issued_at
    ).strftime("%d %B %Y")

    buffer = BytesIO()

    page_width, page_height = landscape(A4)

    pdf = canvas.Canvas(
        buffer,
        pagesize=landscape(A4),
    )

    pdf.setTitle(
        f"SkillHub Certificate - {course.title}"
    )

    # Background
    pdf.setFillColor(
        colors.HexColor("#F8FAFC")
    )
    pdf.rect(
        0,
        0,
        page_width,
        page_height,
        fill=1,
        stroke=0,
    )

    # Outer border
    pdf.setStrokeColor(
        colors.HexColor("#0D6EFD")
    )
    pdf.setLineWidth(5)

    pdf.rect(
        25,
        25,
        page_width - 50,
        page_height - 50,
        fill=0,
        stroke=1,
    )

    # Inner border
    pdf.setStrokeColor(
        colors.HexColor("#94A3B8")
    )
    pdf.setLineWidth(1.5)

    pdf.rect(
        38,
        38,
        page_width - 76,
        page_height - 76,
        fill=0,
        stroke=1,
    )

    # SkillHub heading
    pdf.setFillColor(
        colors.HexColor("#0D6EFD")
    )
    pdf.setFont(
        "Helvetica-Bold",
        24,
    )

    pdf.drawCentredString(
        page_width / 2,
        page_height - 90,
        "SkillHub",
    )

    pdf.setFillColor(
        colors.HexColor("#0F172A")
    )
    pdf.setFont(
        "Helvetica-Bold",
        35,
    )

    pdf.drawCentredString(
        page_width / 2,
        page_height - 145,
        "CERTIFICATE OF COMPLETION",
    )

    pdf.setFillColor(
        colors.HexColor("#475569")
    )
    pdf.setFont(
        "Helvetica",
        15,
    )

    pdf.drawCentredString(
        page_width / 2,
        page_height - 190,
        "This certificate is proudly presented to",
    )

    # Learner name
    pdf.setFillColor(
        colors.HexColor("#0D6EFD")
    )
    pdf.setFont(
        "Helvetica-Bold",
        28,
    )

    learner_lines = simpleSplit(
        learner_name,
        "Helvetica-Bold",
        28,
        page_width - 160,
    )

    learner_y = page_height - 235

    for line in learner_lines:
        pdf.drawCentredString(
            page_width / 2,
            learner_y,
            line,
        )

        learner_y -= 32

    # Course completion text
    pdf.setFillColor(
        colors.HexColor("#475569")
    )
    pdf.setFont(
        "Helvetica",
        15,
    )

    text_y = learner_y - 10

    pdf.drawCentredString(
        page_width / 2,
        text_y,
        "for successfully completing the SkillHub course",
    )

    course_lines = simpleSplit(
        course.title,
        "Helvetica-Bold",
        23,
        page_width - 160,
    )

    course_y = text_y - 42

    pdf.setFillColor(
        colors.HexColor("#0F172A")
    )
    pdf.setFont(
        "Helvetica-Bold",
        23,
    )

    for line in course_lines:
        pdf.drawCentredString(
            page_width / 2,
            course_y,
            line,
        )

        course_y -= 28

    # Bottom information
    information_y = 105

    pdf.setStrokeColor(
        colors.HexColor("#94A3B8")
    )
    pdf.setLineWidth(1)

    pdf.line(
        95,
        information_y + 20,
        285,
        information_y + 20,
    )

    pdf.line(
        page_width - 285,
        information_y + 20,
        page_width - 95,
        information_y + 20,
    )

    pdf.setFillColor(
        colors.HexColor("#0F172A")
    )
    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawCentredString(
        190,
        information_y,
        issue_date,
    )

    pdf.drawCentredString(
        page_width - 190,
        information_y,
        instructor_name,
    )

    pdf.setFillColor(
        colors.HexColor("#64748B")
    )
    pdf.setFont(
        "Helvetica",
        9,
    )

    pdf.drawCentredString(
        190,
        information_y - 15,
        "Date issued",
    )

    pdf.drawCentredString(
        page_width - 190,
        information_y - 15,
        "Course instructor",
    )

    # Certificate number
    pdf.setFont(
        "Helvetica",
        8,
    )

    pdf.drawCentredString(
        page_width / 2,
        60,
        (
            "Certificate number: "
            f"{certificate.certificate_number}"
        ),
    )

    pdf.showPage()
    pdf.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = (
        f"skillhub-certificate-"
        f"{slugify(course.title) or course.pk}.pdf"
    )

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    return response

@login_required
def course_edit(request, course_id):
    """Allow an instructor to edit their draft or rejected course."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course.objects.select_related("category"),
        pk=course_id,
        instructor=request.user,
    )

    editable_statuses = {
        Course.Status.DRAFT,
        Course.Status.REJECTED,
    }

    if course.status not in editable_statuses:
        messages.warning(
            request,
            (
                "Submitted and approved courses cannot be edited. "
                "Only draft or rejected courses can be updated."
            ),
        )

        return redirect(
            "courses:instructor_course_list",
        )

    if request.method == "POST":
        form = CourseCreationForm(
            request.POST,
            instance=course,
        )

        if form.is_valid():
            updated_course = form.save(
                commit=False,
            )

            updated_course.instructor = request.user
            updated_course.status = Course.Status.DRAFT
            updated_course.rejection_reason = ""
            updated_course.save()

            messages.success(
                request,
                "The course information was updated successfully.",
            )

            return redirect(
                "courses:instructor_course_list",
            )

    else:
        form = CourseCreationForm(
            instance=course,
        )

    return render(
        request,
        "courses/course_edit.html",
        {
            "course": course,
            "form": form,
        },
    )

@login_required
def course_enrolled_learners(request, course_id):
    """Display learners enrolled in an instructor's course."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    course = get_object_or_404(
        Course.objects.select_related(
            "category",
            "instructor",
        ),
        pk=course_id,
        instructor=request.user,
    )

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    all_enrollments = (
        Enrollment.objects
        .filter(course=course)
        .select_related("learner")
        .order_by("-enrolled_at")
    )

    total_enrollment_count = (
        all_enrollments.count()
    )

    filtered_enrollments = all_enrollments

    if search_query:
        filtered_enrollments = (
            filtered_enrollments.filter(
                Q(
                    learner__email__icontains=search_query
                )
                | Q(
                    learner__first_name__icontains=search_query
                )
                | Q(
                    learner__last_name__icontains=search_query
                )
            )
        )

    displayed_enrollment_count = (
        filtered_enrollments.count()
    )

    return render(
        request,
        "courses/course_enrolled_learners.html",
        {
            "course": course,
            "enrollments": filtered_enrollments,
            "search_query": search_query,
            "total_enrollment_count": total_enrollment_count,
            "displayed_enrollment_count": (
                displayed_enrollment_count
            ),
        },
    )

@login_required
def instructor_earnings_dashboard(request):
    """Display earnings generated by an instructor's courses."""

    if request.user.role != User.Role.INSTRUCTOR:
        return redirect("accounts:dashboard")

    successful_transactions = (
        PaymentTransaction.objects
        .filter(
            course__instructor=request.user,
            status=PaymentTransaction.Status.SUCCESSFUL,
        )
        .select_related(
            "course",
            "learner",
        )
        .order_by(
            "-completed_at",
            "-created_at",
        )
    )

    summary = successful_transactions.aggregate(
        total_earnings=Coalesce(
            Sum("amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(
                max_digits=12,
                decimal_places=2,
            ),
        ),
        total_sales=Count("pk"),
        unique_learners=Count(
            "learner",
            distinct=True,
        ),
    )

    total_earnings = summary["total_earnings"]
    total_sales = summary["total_sales"]
    unique_learners = summary["unique_learners"]

    if total_sales:
        average_sale = (
            total_earnings
            / Decimal(total_sales)
        )
    else:
        average_sale = Decimal("0.00")

    successful_payment_filter = Q(
        payment_transactions__status=(
            PaymentTransaction.Status.SUCCESSFUL
        )
    )

    course_rows = (
        Course.objects
        .filter(instructor=request.user)
        .select_related("category")
        .annotate(
            successful_sales=Count(
                "payment_transactions",
                filter=successful_payment_filter,
            ),
            earnings=Coalesce(
                Sum(
                    "payment_transactions__amount",
                    filter=successful_payment_filter,
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(
                    max_digits=12,
                    decimal_places=2,
                ),
            ),
        )
        .order_by(
            "-earnings",
            "title",
        )
    )

    recent_transactions = (
        successful_transactions[:10]
    )

    return render(
        request,
        "courses/instructor_earnings_dashboard.html",
        {
            "total_earnings": total_earnings,
            "total_sales": total_sales,
            "unique_learners": unique_learners,
            "average_sale": average_sale,
            "course_rows": course_rows,
            "recent_transactions": recent_transactions,
        },
    )


@login_required
def admin_payment_transactions(request):
    """Allow administrators to monitor platform payments."""

    if (
        request.user.role != User.Role.ADMIN
        and not request.user.is_superuser
    ):
        return redirect("accounts:dashboard")

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    selected_course_value = request.GET.get(
        "course",
        "",
    ).strip()

    selected_course_id = None

    transactions = (
        PaymentTransaction.objects
        .select_related(
            "learner",
            "course",
            "course__instructor",
        )
        .order_by("-created_at")
    )

    # Search by learner email, course title, instructor email,
    # or an exact UUID transaction reference.
    if search_query:
        search_filter = (
            Q(
                learner__email__icontains=search_query
            )
            | Q(
                course__title__icontains=search_query
            )
            | Q(
                course__instructor__email__icontains=search_query
            )
        )

        try:
            reference_uuid = uuid.UUID(
                search_query
            )
        except (ValueError, TypeError, AttributeError):
            reference_uuid = None

        if reference_uuid is not None:
            search_filter |= Q(
                reference=reference_uuid
            )

        transactions = transactions.filter(
            search_filter
        )

    valid_statuses = {
        value
        for value, _label
        in PaymentTransaction.Status.choices
    }

    if selected_status in valid_statuses:
        transactions = transactions.filter(
            status=selected_status
        )
    else:
        selected_status = ""

    if selected_course_value.isdigit():
        selected_course_id = int(
            selected_course_value
        )

        transactions = transactions.filter(
            course_id=selected_course_id
        )

    summary = transactions.aggregate(
        total_transactions=Count("pk"),

        successful_transactions=Count(
            "pk",
            filter=Q(
                status=(
                    PaymentTransaction
                    .Status
                    .SUCCESSFUL
                )
            ),
        ),

        pending_transactions=Count(
            "pk",
            filter=Q(
                status=(
                    PaymentTransaction
                    .Status
                    .PENDING
                )
            ),
        ),

        failed_transactions=Count(
            "pk",
            filter=Q(
                status=(
                    PaymentTransaction
                    .Status
                    .FAILED
                )
            ),
        ),

        successful_revenue=Coalesce(
            Sum(
                "amount",
                filter=Q(
                    status=(
                        PaymentTransaction
                        .Status
                        .SUCCESSFUL
                    )
                ),
            ),
            Value(
                Decimal("0.00")
            ),
            output_field=DecimalField(
                max_digits=14,
                decimal_places=2,
            ),
        ),
    )

    status_options = [
        {
            "value": "",
            "label": "All statuses",
            "selected": selected_status == "",
        }
    ]

    status_options.extend(
        {
            "value": value,
            "label": label,
            "selected": value == selected_status,
        }
        for value, label
        in PaymentTransaction.Status.choices
    )

    course_queryset = (
        Course.objects
        .filter(
            payment_transactions__isnull=False
        )
        .select_related("instructor")
        .distinct()
        .order_by("title")
    )

    course_options = [
        {
            "id": course.pk,
            "title": course.title,
            "instructor_email": (
                course.instructor.email
            ),
            "selected": (
                course.pk == selected_course_id
            ),
        }
        for course in course_queryset
    ]

    paginator = Paginator(
        transactions,
        20,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    status_css_classes = {
        PaymentTransaction.Status.SUCCESSFUL: (
            "text-bg-success"
        ),
        PaymentTransaction.Status.PENDING: (
            "text-bg-warning"
        ),
        PaymentTransaction.Status.FAILED: (
            "text-bg-danger"
        ),
    }

    transaction_rows = [
        {
            "transaction": transaction,
            "status_class": (
                status_css_classes.get(
                    transaction.status,
                    "text-bg-secondary",
                )
            ),
        }
        for transaction in page_obj.object_list
    ]

    pagination_parameters = (
        request.GET.copy()
    )

    pagination_parameters.pop(
        "page",
        None,
    )

    pagination_query = (
        pagination_parameters.urlencode()
    )

    filters_are_active = bool(
        search_query
        or selected_status
        or selected_course_id
    )

    return render(
        request,
        "courses/admin_payment_transactions.html",
        {
            "transaction_rows": transaction_rows,
            "page_obj": page_obj,
            "search_query": search_query,
            "status_options": status_options,
            "course_options": course_options,
            "selected_status": selected_status,
            "selected_course_id": (
                selected_course_id
            ),
            "filters_are_active": (
                filters_are_active
            ),
            "pagination_query": (
                pagination_query
            ),
            "total_transactions": (
                summary["total_transactions"]
            ),
            "successful_transactions": (
                summary[
                    "successful_transactions"
                ]
            ),
            "pending_transactions": (
                summary[
                    "pending_transactions"
                ]
            ),
            "failed_transactions": (
                summary[
                    "failed_transactions"
                ]
            ),
            "successful_revenue": (
                summary[
                    "successful_revenue"
                ]
            ),
        },
    )

def _apply_report_date_filter(
    queryset,
    field_name,
    start_date,
    end_date,
):
    """Apply optional start and end dates to a queryset."""

    filters = {}

    if start_date:
        filters[f"{field_name}__date__gte"] = start_date

    if end_date:
        filters[f"{field_name}__date__lte"] = end_date

    if filters:
        queryset = queryset.filter(**filters)

    return queryset


@login_required
def admin_platform_reports(request):
    """Display and export platform reports for administrators."""

    if (
        request.user.role != User.Role.ADMIN
        and not request.user.is_superuser
    ):
        return redirect("accounts:dashboard")

    start_value = request.GET.get(
        "start_date",
        "",
    ).strip()

    end_value = request.GET.get(
        "end_date",
        "",
    ).strip()

    start_date = (
        parse_date(start_value)
        if start_value
        else None
    )

    end_date = (
        parse_date(end_value)
        if end_value
        else None
    )

    invalid_date_filter = False

    if start_value and start_date is None:
        invalid_date_filter = True
        start_value = ""

    if end_value and end_date is None:
        invalid_date_filter = True
        end_value = ""

    if (
        start_date
        and end_date
        and start_date > end_date
    ):
        invalid_date_filter = True

        start_date = None
        end_date = None
        start_value = ""
        end_value = ""

    if invalid_date_filter:
        messages.warning(
            request,
            (
                "The selected report dates were invalid. "
                "The complete report is being displayed."
            ),
        )

    learners = User.objects.filter(
        role=User.Role.LEARNER,
    )

    instructors = User.objects.filter(
        role=User.Role.INSTRUCTOR,
    )

    courses = Course.objects.all()

    approved_courses = Course.objects.filter(
        status=Course.Status.APPROVED,
    )

    enrollments = Enrollment.objects.all()

    reviews = CourseReview.objects.all()

    certificates = Certificate.objects.all()

    all_transactions = (
        PaymentTransaction.objects.all()
    )

    successful_transactions = (
        all_transactions.filter(
            status=(
                PaymentTransaction
                .Status
                .SUCCESSFUL
            ),
        )
    )

    pending_transactions = (
        all_transactions.filter(
            status=(
                PaymentTransaction
                .Status
                .PENDING
            ),
        )
    )

    failed_transactions = (
        all_transactions.filter(
            status=(
                PaymentTransaction
                .Status
                .FAILED
            ),
        )
    )

    learners = _apply_report_date_filter(
        learners,
        "date_joined",
        start_date,
        end_date,
    )

    instructors = _apply_report_date_filter(
        instructors,
        "date_joined",
        start_date,
        end_date,
    )

    courses = _apply_report_date_filter(
        courses,
        "created_at",
        start_date,
        end_date,
    )

    approved_courses_in_period = (
        _apply_report_date_filter(
            approved_courses,
            "created_at",
            start_date,
            end_date,
        )
    )

    enrollments = _apply_report_date_filter(
        enrollments,
        "enrolled_at",
        start_date,
        end_date,
    )

    reviews = _apply_report_date_filter(
        reviews,
        "created_at",
        start_date,
        end_date,
    )

    certificates = _apply_report_date_filter(
        certificates,
        "issued_at",
        start_date,
        end_date,
    )

    successful_transactions = (
        _apply_report_date_filter(
            successful_transactions,
            "created_at",
            start_date,
            end_date,
        )
    )

    pending_transactions = (
        _apply_report_date_filter(
            pending_transactions,
            "created_at",
            start_date,
            end_date,
        )
    )

    failed_transactions = (
        _apply_report_date_filter(
            failed_transactions,
            "created_at",
            start_date,
            end_date,
        )
    )

    payment_summary = (
        successful_transactions.aggregate(
            revenue=Coalesce(
                Sum("amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            ),
            sales=Count("pk"),
            paying_learners=Count(
                "learner",
                distinct=True,
            ),
        )
    )

    total_revenue = payment_summary["revenue"]
    successful_sales = payment_summary["sales"]
    paying_learners = payment_summary[
        "paying_learners"
    ]

    if successful_sales:
        average_sale = (
            total_revenue
            / Decimal(successful_sales)
        )
    else:
        average_sale = Decimal("0.00")

    enrollment_statistics = {
        row["course_id"]: row["total"]
        for row in (
            enrollments
            .values("course_id")
            .annotate(total=Count("pk"))
        )
    }

    review_statistics = {
        row["course_id"]: {
            "review_count": row[
                "review_count"
            ],
            "average_rating": row[
                "average_rating"
            ],
        }
        for row in (
            reviews
            .values("course_id")
            .annotate(
                review_count=Count("pk"),
                average_rating=Avg("rating"),
            )
        )
    }

    payment_statistics = {
        row["course_id"]: {
            "sales": row["sales"],
            "revenue": row["revenue"],
        }
        for row in (
            successful_transactions
            .values("course_id")
            .annotate(
                sales=Count("pk"),
                revenue=Coalesce(
                    Sum("amount"),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(
                        max_digits=14,
                        decimal_places=2,
                    ),
                ),
            )
        )
    }

    certificate_statistics = {
        row["course_id"]: row["total"]
        for row in (
            certificates
            .values("course_id")
            .annotate(total=Count("pk"))
        )
    }

    course_rows = []

    report_courses = (
        approved_courses
        .select_related(
            "category",
            "instructor",
        )
        .order_by("title")
    )

    for course in report_courses:
        review_data = review_statistics.get(
            course.pk,
            {},
        )

        payment_data = payment_statistics.get(
            course.pk,
            {},
        )

        course_rows.append(
            {
                "course": course,
                "enrollment_count": (
                    enrollment_statistics.get(
                        course.pk,
                        0,
                    )
                ),
                "review_count": (
                    review_data.get(
                        "review_count",
                        0,
                    )
                ),
                "average_rating": (
                    review_data.get(
                        "average_rating"
                    )
                ),
                "successful_sales": (
                    payment_data.get(
                        "sales",
                        0,
                    )
                ),
                "revenue": (
                    payment_data.get(
                        "revenue",
                        Decimal("0.00"),
                    )
                ),
                "certificate_count": (
                    certificate_statistics.get(
                        course.pk,
                        0,
                    )
                ),
            }
        )

    course_rows.sort(
        key=lambda row: (
            row["revenue"],
            row["enrollment_count"],
        ),
        reverse=True,
    )

    recent_transactions = (
        successful_transactions
        .select_related(
            "learner",
            "course",
            "course__instructor",
        )
        .order_by(
            "-completed_at",
            "-created_at",
        )[:10]
    )

    summary = {
        "learner_count": learners.count(),
        "instructor_count": instructors.count(),
        "course_count": courses.count(),
        "approved_course_count": (
            approved_courses_in_period.count()
        ),
        "enrollment_count": enrollments.count(),
        "review_count": reviews.count(),
        "certificate_count": (
            certificates.count()
        ),
        "successful_sales": successful_sales,
        "pending_payment_count": (
            pending_transactions.count()
        ),
        "failed_payment_count": (
            failed_transactions.count()
        ),
        "paying_learners": paying_learners,
        "total_revenue": total_revenue,
        "average_sale": average_sale,
    }

    if request.GET.get("format") == "csv":
        response = HttpResponse(
            content_type=(
                "text/csv; charset=utf-8"
            ),
        )

        response["Content-Disposition"] = (
            'attachment; '
            'filename="skillhub-platform-report.csv"'
        )

        response.write("\ufeff")

        writer = csv.writer(response)

        writer.writerow(
            [
                "SkillHub Platform Report",
            ]
        )

        writer.writerow(
            [
                "Start date",
                start_value or "All time",
            ]
        )

        writer.writerow(
            [
                "End date",
                end_value or "All time",
            ]
        )

        writer.writerow([])

        writer.writerow(
            [
                "Metric",
                "Value",
            ]
        )

        writer.writerow(
            [
                "Learners",
                summary["learner_count"],
            ]
        )

        writer.writerow(
            [
                "Instructors",
                summary["instructor_count"],
            ]
        )

        writer.writerow(
            [
                "Courses created",
                summary["course_count"],
            ]
        )

        writer.writerow(
            [
                "Approved courses",
                summary[
                    "approved_course_count"
                ],
            ]
        )

        writer.writerow(
            [
                "Enrollments",
                summary["enrollment_count"],
            ]
        )

        writer.writerow(
            [
                "Reviews",
                summary["review_count"],
            ]
        )

        writer.writerow(
            [
                "Certificates",
                summary[
                    "certificate_count"
                ],
            ]
        )

        writer.writerow(
            [
                "Successful sales",
                summary["successful_sales"],
            ]
        )

        writer.writerow(
            [
                "Successful revenue",
                summary["total_revenue"],
            ]
        )

        writer.writerow(
            [
                "Pending payments",
                summary[
                    "pending_payment_count"
                ],
            ]
        )

        writer.writerow(
            [
                "Failed payments",
                summary[
                    "failed_payment_count"
                ],
            ]
        )

        writer.writerow([])

        writer.writerow(
            [
                "Course",
                "Instructor",
                "Category",
                "Enrollments",
                "Reviews",
                "Average rating",
                "Successful sales",
                "Revenue",
                "Certificates",
            ]
        )

        for row in course_rows:
            writer.writerow(
                [
                    row["course"].title,
                    row[
                        "course"
                    ].instructor.email,
                    row[
                        "course"
                    ].category.name,
                    row["enrollment_count"],
                    row["review_count"],
                    (
                        round(
                            row[
                                "average_rating"
                            ],
                            2,
                        )
                        if row[
                            "average_rating"
                        ] is not None
                        else ""
                    ),
                    row["successful_sales"],
                    row["revenue"],
                    row[
                        "certificate_count"
                    ],
                ]
            )

        return response

    query_parameters = request.GET.copy()

    query_parameters.pop(
        "format",
        None,
    )

    report_query = (
        query_parameters.urlencode()
    )

    filters_are_active = bool(
        start_date or end_date
    )

    return render(
        request,
        "courses/admin_platform_reports.html",
        {
            "summary": summary,
            "course_rows": course_rows,
            "recent_transactions": (
                recent_transactions
            ),
            "start_value": start_value,
            "end_value": end_value,
            "filters_are_active": (
                filters_are_active
            ),
            "report_query": report_query,
        },
    )

def _build_personalized_recommendations(
    learner,
    limit=6,
):
    """Return personalized approved-course recommendations."""

    enrolled_courses = list(
        Course.objects.filter(
            enrollments__learner=learner,
        )
        .select_related("category")
        .distinct()
    )

    enrolled_course_ids = {
        course.pk
        for course in enrolled_courses
    }

    category_preferences = Counter()
    level_preferences = Counter()

    # Enrollment history gives information about learner interests.
    for course in enrolled_courses:
        category_preferences[
            course.category_id
        ] += 2

        level_preferences[
            course.level
        ] += 1

    # Positive reviews provide a stronger preference signal.
    positive_reviews = (
        CourseReview.objects.filter(
            learner=learner,
            rating__gte=4,
        )
        .select_related(
            "course",
            "course__category",
        )
    )

    for review in positive_reviews:
        category_preferences[
            review.course.category_id
        ] += 3

        level_preferences[
            review.course.level
        ] += 2

    has_learning_history = bool(
        enrolled_courses
        or category_preferences
        or level_preferences
    )

    candidate_courses = list(
        Course.objects.filter(
            status=Course.Status.APPROVED,
        )
        .exclude(
            pk__in=enrolled_course_ids,
        )
        .select_related(
            "category",
            "instructor",
        )
        .order_by("title")
    )

    candidate_ids = [
        course.pk
        for course in candidate_courses
    ]

    enrollment_statistics = {
        row["course_id"]: row["total"]
        for row in (
            Enrollment.objects.filter(
                course_id__in=candidate_ids,
            )
            .values("course_id")
            .annotate(
                total=Count("pk"),
            )
        )
    }

    review_statistics = {
        row["course_id"]: {
            "average_rating": (
                row["average_rating"]
            ),
            "review_count": (
                row["review_count"]
            ),
        }
        for row in (
            CourseReview.objects.filter(
                course_id__in=candidate_ids,
            )
            .values("course_id")
            .annotate(
                average_rating=Avg("rating"),
                review_count=Count("pk"),
            )
        )
    }

    recommendations = []

    for course in candidate_courses:
        category_strength = (
            category_preferences.get(
                course.category_id,
                0,
            )
        )

        level_strength = (
            level_preferences.get(
                course.level,
                0,
            )
        )

        review_data = review_statistics.get(
            course.pk,
            {},
        )

        average_rating = (
            review_data.get(
                "average_rating"
            )
            or 0
        )

        review_count = review_data.get(
            "review_count",
            0,
        )

        enrollment_count = (
            enrollment_statistics.get(
                course.pk,
                0,
            )
        )

        recommendation_score = (
            category_strength * 4
            + level_strength * 2
            + float(average_rating) * 1.5
            + min(enrollment_count, 20) * 0.2
            + min(review_count, 10) * 0.1
        )

        if category_strength and level_strength:
            reason = (
                f"Matches your interest in "
                f"{course.category.name} and your "
                f"preferred course level."
            )

        elif category_strength:
            reason = (
                f"Recommended because you have shown "
                f"interest in {course.category.name}."
            )

        elif level_strength:
            reason = (
                f"Matches the difficulty level of "
                f"courses you previously selected."
            )

        elif average_rating:
            reason = (
                f"Popular with learners and rated "
                f"{float(average_rating):.1f} out of 5."
            )

        elif enrollment_count:
            reason = (
                "Recommended because it is popular "
                "among SkillHub learners."
            )

        else:
            reason = (
                "A recently available approved course "
                "you have not joined yet."
            )

        recommendations.append(
            {
                "course": course,
                "score": recommendation_score,
                "reason": reason,
                "average_rating": average_rating,
                "review_count": review_count,
                "enrollment_count": enrollment_count,
            }
        )

    recommendations.sort(
        key=lambda recommendation: (
            recommendation["score"],
            recommendation["average_rating"],
            recommendation["enrollment_count"],
            recommendation["course"].created_at,
        ),
        reverse=True,
    )

    return (
        recommendations[:limit],
        has_learning_history,
    )

@login_required
def personalized_course_recommendations(request):
    """Display personalized course recommendations for a learner."""

    if request.user.role != User.Role.LEARNER:
        return redirect("accounts:dashboard")

    recommendations, has_learning_history = (
        _build_personalized_recommendations(
            request.user,
            limit=6,
        )
    )

    enrolled_course_count = (
        Enrollment.objects.filter(
            learner=request.user,
        )
        .values("course_id")
        .distinct()
        .count()
    )

    return render(
        request,
        "courses/personalized_course_recommendations.html",
        {
            "recommendations": recommendations,
            "has_learning_history": (
                has_learning_history
            ),
            "enrolled_course_count": (
                enrolled_course_count
            ),
        },
    )