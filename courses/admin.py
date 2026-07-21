from django.contrib import admin, messages

from .forms import CourseAdminReviewForm
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

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
    )

    search_fields = (
        "name",
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminReviewForm

    list_display = (
        "title",
        "instructor",
        "category",
        "level",
        "price",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "level",
        "category",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "instructor__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    actions = (
        "approve_submitted_courses",
        "reject_submitted_courses",
    )

    @admin.action(
        description="Approve selected submitted courses"
    )
    def approve_submitted_courses(
        self,
        request,
        queryset,
    ):
        submitted_courses = queryset.filter(
            status=Course.Status.SUBMITTED
        )

        updated_count = submitted_courses.update(
            status=Course.Status.APPROVED,
            rejection_reason="",
        )

        skipped_count = queryset.count() - updated_count

        if updated_count:
            self.message_user(
                request,
                (
                    f"{updated_count} course(s) "
                    "approved successfully."
                ),
                level=messages.SUCCESS,
            )

        if skipped_count:
            self.message_user(
                request,
                (
                    f"{skipped_count} course(s) were skipped "
                    "because they were not submitted."
                ),
                level=messages.WARNING,
            )

    @admin.action(
        description="Reject selected submitted courses"
    )
    def reject_submitted_courses(
        self,
        request,
        queryset,
    ):
        submitted_courses = queryset.filter(
            status=Course.Status.SUBMITTED
        )

        updated_count = submitted_courses.update(
            status=Course.Status.REJECTED,
            rejection_reason=(
                "The course was rejected by an administrator. "
                "Please review the course information before "
                "submitting it again."
            ),
        )

        skipped_count = queryset.count() - updated_count

        if updated_count:
            self.message_user(
                request,
                (
                    f"{updated_count} course(s) "
                    "rejected successfully."
                ),
                level=messages.SUCCESS,
            )

        if skipped_count:
            self.message_user(
                request,
                (
                    f"{skipped_count} course(s) were skipped "
                    "because they were not submitted."
                ),
                level=messages.WARNING,
            )

@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "order",
        "created_at",
    )

    list_filter = (
        "course",
    )

    search_fields = (
        "title",
        "course__title",
    )

    ordering = (
        "course",
        "order",
    )


@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "section",
        "order",
        "duration_minutes",
        "is_preview",
        "created_at",
    )

    list_filter = (
        "is_preview",
        "section__course",
    )

    search_fields = (
        "title",
        "section__title",
        "section__course__title",
    )

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "learner",
        "course",
        "status",
        "enrolled_at",
    )

    list_filter = (
        "status",
        "course",
        "enrolled_at",
    )

    search_fields = (
        "learner__email",
        "course__title",
    )

    readonly_fields = (
        "enrolled_at",
    )

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "learner",
        "course",
        "amount",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "reference",
        "learner__email",
        "course__title",
    )

    readonly_fields = (
        "reference",
        "learner",
        "course",
        "amount",
        "status",
        "created_at",
        "completed_at",
    )

@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = (
        "learner",
        "course",
        "rating",
        "updated_at",
    )

    list_filter = (
        "rating",
        "updated_at",
    )

    search_fields = (
        "learner__email",
        "course__title",
        "comment",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "passing_score",
        "is_published",
        "created_at",
    )

    list_filter = (
        "is_published",
        "course",
    )

    search_fields = (
        "title",
        "course__title",
    )


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "quiz",
        "order",
        "text",
        "correct_option",
    )

    list_filter = (
        "quiz__course",
    )

    search_fields = (
        "text",
        "quiz__title",
    )

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "learner",
        "quiz",
        "score",
        "correct_answers",
        "total_questions",
        "passed",
        "completed_at",
    )

    list_filter = (
        "passed",
        "completed_at",
        "quiz",
    )

    search_fields = (
        "learner__email",
        "quiz__title",
        "quiz__course__title",
    )

    readonly_fields = (
        "learner",
        "quiz",
        "score",
        "correct_answers",
        "total_questions",
        "passed",
        "completed_at",
    )


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "attempt",
        "question",
        "selected_option",
        "is_correct",
    )

    list_filter = (
        "is_correct",
        "selected_option",
    )

    search_fields = (
        "attempt__learner__email",
        "question__text",
    )

    readonly_fields = (
        "attempt",
        "question",
        "selected_option",
        "is_correct",
    )

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_number",
        "learner",
        "course",
        "issued_at",
    )

    list_filter = (
        "issued_at",
        "course",
    )

    search_fields = (
        "certificate_number",
        "learner__email",
        "course__title",
    )

    readonly_fields = (
        "certificate_number",
        "learner",
        "course",
        "issued_at",
    )