from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)
from .models import InstructorProfile, LearnerProfile, User
from django.db import transaction


class CustomUserCreationForm(UserCreationForm):
    """Form used when administrators create users."""

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "role",
            "account_status",
        )

    def clean_email(self):
        email = self.cleaned_data["email"]
        return email.strip().lower()


class CustomUserChangeForm(UserChangeForm):
    """Form used when administrators update users."""

    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self):
        email = self.cleaned_data["email"]
        return email.strip().lower()
    
class SkillHubAuthenticationForm(AuthenticationForm):
    """Authentication form using the user's email address."""

    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )

    error_messages = {
        "invalid_login": (
            "Unable to log in with these credentials. "
            "Check your email and password, or contact support "
            "if your account is unavailable."
        ),
        "inactive": "This account is inactive.",
    }

    def clean_username(self):
        """Normalize the email address before authentication."""

        return self.cleaned_data["username"].strip().lower()
    
class LearnerRegistrationForm(UserCreationForm):
    """Public registration form for new SkillHub learners."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your first name",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your last name",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
                "autocomplete": "email",
            }
        ),
    )

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Create a secure password",
                "autocomplete": "new-password",
            }
        ),
        help_text=(
            "Use at least 8 characters. Avoid common passwords and "
            "passwords made only from numbers."
        ),
    )

    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password again",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
        )

    def clean_email(self):
        """Normalize the email and reject duplicate accounts."""

        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    @transaction.atomic
    def save(self, commit=True):
        """Create a learner account and its learner profile."""

        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.role = User.Role.LEARNER
        user.account_status = User.AccountStatus.ACTIVE
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()

            LearnerProfile.objects.get_or_create(
                user=user,
            )

        return user
    
class InstructorRegistrationForm(UserCreationForm):
    """Public registration form for new SkillHub instructors."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your first name",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your last name",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
                "autocomplete": "email",
            }
        ),
    )

    professional_title = forms.CharField(
        max_length=150,
        required=True,
        label="Professional title",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "For example: Software Engineer",
            }
        ),
    )

    expertise = forms.CharField(
        max_length=200,
        required=True,
        label="Area of expertise",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "For example: Python and Web Development",
            }
        ),
    )

    biography = forms.CharField(
        max_length=1000,
        required=True,
        label="Professional biography",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Briefly describe your experience and qualifications"
                ),
                "rows": 4,
            }
        ),
    )

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Create a secure password",
                "autocomplete": "new-password",
            }
        ),
        help_text=(
            "Use at least 8 characters. Avoid common passwords and "
            "passwords made only from numbers."
        ),
    )

    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password again",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
        )

    def clean_email(self):
        """Normalize the email and prevent duplicate accounts."""

        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    def clean_professional_title(self):
        title = self.cleaned_data["professional_title"].strip()

        if len(title) < 3:
            raise forms.ValidationError(
                "The professional title must contain at least 3 characters."
            )

        return title

    def clean_expertise(self):
        expertise = self.cleaned_data["expertise"].strip()

        if len(expertise) < 3:
            raise forms.ValidationError(
                "The area of expertise must contain at least 3 characters."
            )

        return expertise

    def clean_biography(self):
        biography = self.cleaned_data["biography"].strip()

        if len(biography) < 20:
            raise forms.ValidationError(
                "The biography must contain at least 20 characters."
            )

        return biography

    @transaction.atomic
    def save(self, commit=True):
        """Create the user and related instructor profile together."""

        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.role = User.Role.INSTRUCTOR
        user.account_status = User.AccountStatus.ACTIVE
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()

            InstructorProfile.objects.create(
                user=user,
                professional_title=self.cleaned_data[
                    "professional_title"
                ],
                expertise=self.cleaned_data["expertise"],
                biography=self.cleaned_data["biography"],
            )

        return user
    
class LearnerProfileUpdateForm(forms.ModelForm):
    """Allow learners to update their personal profile."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your first name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your last name",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
            }
        ),
    )

    class Meta:
        model = LearnerProfile

        fields = (
            "profile_picture",
            "skills",
            "phone_number",
            "location",
            "biography",
        )

        widgets = {
            "profile_picture": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
            "skills": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Python, Django, Data Analysis",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+49 ...",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Leipzig, Germany",
                }
            ),
            "biography": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Tell instructors and learners a little "
                        "about yourself."
                    ),
                }
            ),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user

        super().__init__(*args, **kwargs)

        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        duplicate_exists = (
            User.objects
            .filter(email__iexact=email)
            .exclude(pk=self.user.pk)
            .exists()
        )

        if duplicate_exists:
            raise forms.ValidationError(
                "Another account already uses this email address."
            )

        return email

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")

        if picture and hasattr(picture, "size"):
            maximum_size = 2 * 1024 * 1024

            if picture.size > maximum_size:
                raise forms.ValidationError(
                    "The profile picture must be 2 MB or smaller."
                )

        return picture

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=False)

        self.user.first_name = self.cleaned_data[
            "first_name"
        ].strip()

        self.user.last_name = self.cleaned_data[
            "last_name"
        ].strip()

        self.user.email = self.cleaned_data["email"]

        if commit:
            self.user.save()
            profile.save()

        return profile