from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for creating SkillHub users and administrators."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a user using an email and password."""

        if not email:
            raise ValueError("The email address is required.")

        if not password:
            raise ValueError("The password is required.")

        email = self.normalize_email(email).strip().lower()

        user = self.model(
            email=email,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a normal SkillHub user."""

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("account_status", "ACTIVE")

        return self._create_user(
            email=email,
            password=password,
            **extra_fields,
        )

    def create_superuser(self, email, password=None, **extra_fields):
        """Create a SkillHub administrator."""

        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("account_status", "ACTIVE")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self._create_user(
            email=email,
            password=password,
            **extra_fields,
        )