from django.conf import settings
from django.db import models
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
)
import uuid

def course_video_upload_path(instance, filename):
    """Store course videos in folders organized by course and section."""

    return (
        f"courses/{instance.section.course_id}/"
        f"sections/{instance.section_id}/{filename}"
    )

class Category(models.Model):
    """Category used to organize SkillHub courses."""

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Course(models.Model):
    """A course created by a SkillHub instructor."""

    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted for approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_courses",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    duration_minutes = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(1)],
        help_text="Estimated course duration in minutes.",
    )

    learning_objectives = models.TextField(
        help_text="Enter one learning objective per line.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == 0
    
    @property
    def duration_display(self):
        """Return the course duration in a readable format."""

        hours, minutes = divmod(self.duration_minutes, 60)

        if hours and minutes:
            return f"{hours} hr {minutes} min"

        if hours:
            unit = "hr" if hours == 1 else "hrs"
            return f"{hours} {unit}"

        return f"{minutes} min"
    
class CourseSection(models.Model):
    """A section used to organize lessons inside a course."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    title = models.CharField(
        max_length=200,
    )

    order = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ("order", "id")

        constraints = [
            models.UniqueConstraint(
                fields=("course", "order"),
                name="unique_section_order_per_course",
            )
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class VideoLesson(models.Model):
    """A video lesson belonging to a course section."""

    section = models.ForeignKey(
        CourseSection,
        on_delete=models.CASCADE,
        related_name="lessons",
    )

    title = models.CharField(
        max_length=200,
    )

    video_file = models.FileField(
        upload_to=course_video_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "mp4",
                    "webm",
                    "mov",
                    "m4v",
                ]
            )
        ],
    )

    order = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    duration_minutes = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    is_preview = models.BooleanField(
        default=False,
        help_text=(
            "Allow visitors to preview this lesson "
            "without enrolling."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ("order", "id")

        constraints = [
            models.UniqueConstraint(
                fields=("section", "order"),
                name="unique_lesson_order_per_section",
            )
        ]

    def __str__(self):
        return f"{self.section.title} - {self.title}"
    

class Enrollment(models.Model):
    """Connect a learner with a course they joined."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"

    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_enrollments",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    enrolled_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ("-enrolled_at",)

        constraints = [
            models.UniqueConstraint(
                fields=("learner", "course"),
                name="unique_learner_course_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.learner.email} - {self.course.title}"

class PaymentTransaction(models.Model):
    """A simulated payment for purchasing a SkillHub course."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        FAILED = "FAILED", "Failed"

    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )

    reference = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return (
            f"{self.learner.email} - "
            f"{self.course.title} - "
            f"{self.get_status_display()}"
        )