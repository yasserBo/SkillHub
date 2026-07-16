from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager

class User(AbstractUser):

    """Main SkillHub user model."""

    class Role(models.TextChoices):
        LEARNER = "LEARNER", "Learner"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"
        ADMIN = "ADMIN", "Administrator"

    class AccountStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        DEACTIVATED = "DEACTIVATED", "Deactivated"

    # SkillHub uses email instead of username.
    username = None

    email = models.EmailField(
        unique=True,
        help_text="The email address used to access SkillHub.",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.LEARNER,
    )

    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )

    objects = UserManager()
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        """Normalize the email and synchronize account activity."""

        if self.email:
            self.email = self.email.strip().lower()

        self.is_active = (
            self.account_status == self.AccountStatus.ACTIVE
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    @property
    def is_learner(self):
        return self.role == self.Role.LEARNER

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_administrator(self):
        return self.role == self.Role.ADMIN
    
class InstructorProfile(models.Model):
    """Professional information belonging to a SkillHub instructor."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )

    professional_title = models.CharField(
        max_length=150,
        help_text="For example: Software Engineer or Data Scientist.",
    )

    expertise = models.CharField(
        max_length=200,
        help_text="The instructor's main teaching area.",
    )

    biography = models.TextField(
        max_length=1000,
        help_text="A short professional biography.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - Instructor Profile"