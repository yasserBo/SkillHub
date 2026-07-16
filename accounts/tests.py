from urllib import response

from django.test import TestCase
from django.urls import reverse

from .models import InstructorProfile, User

class LearnerRegistrationTests(TestCase):
    def setUp(self):
        self.registration_url = reverse(
            "accounts:learner_register"
        )

        self.valid_data = {
            "first_name": "Test",
            "last_name": "Learner",
            "email": "learner@skillhub.com",
            "password1": "V7@qL2#rP9$xM4",
            "password2": "V7@qL2#rP9$xM4",
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

class InstructorRegistrationTests(TestCase):
    """Tests for US-14 instructor account registration."""

    def setUp(self):
        self.registration_url = reverse(
            "accounts:instructor_register"
        )

        self.valid_data = {
            "first_name": "Test",
            "last_name": "Instructor",
            "email": "instructor@skillhub.com",
            "professional_title": "Software Engineer",
            "expertise": "Python and Web Development",
            "biography": (
                "I am an experienced software engineer "
                "and technical instructor."
            ),
            "password1": "Mango7!River#Cloud92",
            "password2": "Mango7!River#Cloud92",
        }

    def test_instructor_registration_page_opens(self):
        response = self.client.get(self.registration_url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "accounts/instructor_register.html",
        )

    def test_valid_instructor_registration(self):
        response = self.client.post(
            self.registration_url,
            data=self.valid_data,
        )


        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )

        user = User.objects.get(
            email="instructor@skillhub.com"
        )

        self.assertEqual(
            user.role,
            User.Role.INSTRUCTOR,
        )

        self.assertEqual(
            user.account_status,
            User.AccountStatus.ACTIVE,
        )

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_instructor_profile_is_created(self):
        self.client.post(
            self.registration_url,
            data=self.valid_data,
        )

        user = User.objects.get(
            email="instructor@skillhub.com"
        )

        profile = user.instructor_profile

        self.assertEqual(
            profile.professional_title,
            "Software Engineer",
        )

        self.assertEqual(
            profile.expertise,
            "Python and Web Development",
        )

        self.assertIn(
            "experienced software engineer",
            profile.biography,
        )

    def test_instructor_password_is_hashed(self):
        self.client.post(
            self.registration_url,
            data=self.valid_data,
        )

        user = User.objects.get(
            email="instructor@skillhub.com"
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

    def test_duplicate_instructor_email_is_rejected(self):
        User.objects.create_user(
            email="instructor@skillhub.com",
            password="ExistingInstructor2026!",
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
                email="instructor@skillhub.com"
            ).count(),
            1,
        )

        self.assertEqual(
            InstructorProfile.objects.count(),
            0,
        )

    def test_short_biography_is_rejected(self):
        invalid_data = self.valid_data.copy()
        invalid_data["biography"] = "Too short"

        response = self.client.post(
            self.registration_url,
            data=invalid_data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "The biography must contain at least 20 characters.",
        )

        self.assertFalse(
            User.objects.filter(
                email="instructor@skillhub.com"
            ).exists()
        )

    def test_mismatched_passwords_are_rejected(self):
        invalid_data = self.valid_data.copy()
        invalid_data["password2"] = "DifferentPassword2026!"

        response = self.client.post(
            self.registration_url,
            data=invalid_data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            User.objects.filter(
                email="instructor@skillhub.com"
            ).exists()
        )

        self.assertEqual(
            InstructorProfile.objects.count(),
            0,
        )