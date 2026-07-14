from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


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

    def save(self, commit=True):
        """Create a normal learner account."""

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

        return user