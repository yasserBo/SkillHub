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