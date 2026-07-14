from django.test import TestCase
from django.urls import reverse

from .models import User


class LearnerRegistrationTests(TestCase):
    def setUp(self):
        self.registration_url = reverse(
            "accounts:learner_register"
        )

        self.valid_data = {
            "first_name": "Test",
            "last_name": "Learner",
            "email": "learner@skillhub.com",
            "password1": "SkillHubTest2026!",
            "password2": "SkillHubTest2026!",
        }

    def test_registration_page_opens(self):
        response = self.client.get(self.registration_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/learner_register.html",
        )

    def test_valid_learner_registration(self):
        response = self.client.post(
            self.registration_url,
            data=self.valid_data,
        )

        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )

        user = User.objects.get(
            email="learner@skillhub.com"
        )

        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertEqual(
            user.account_status,
            User.AccountStatus.ACTIVE,
        )
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_is_hashed(self):
        self.client.post(
            self.registration_url,
            data=self.valid_data,
        )

        user = User.objects.get(
            email="learner@skillhub.com"
        )

        self.assertNotEqual(
            user.password,
            self.valid_data["password1"],
        )

        self.assertTrue(
            user.check_password(
                self.valid_data["password1"]
            )
        )

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="learner@skillhub.com",
            password="ExistingPassword2026!",
        )

        response = self.client.post(
            self.registration_url,
            data=self.valid_data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "An account with this email address already exists.",
        )

        self.assertEqual(
            User.objects.filter(
                email="learner@skillhub.com"
            ).count(),
            1,
        )

    def test_invalid_email_is_rejected(self):
        invalid_data = self.valid_data.copy()
        invalid_data["email"] = "invalid-email"

        response = self.client.post(
            self.registration_url,
            data=invalid_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_mismatched_passwords_are_rejected(self):
        invalid_data = self.valid_data.copy()
        invalid_data["password2"] = "DifferentPassword2026!"

        response = self.client.post(
            self.registration_url,
            data=invalid_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_missing_first_name_is_rejected(self):
        invalid_data = self.valid_data.copy()
        invalid_data["first_name"] = ""

        response = self.client.post(
            self.registration_url,
            data=invalid_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())