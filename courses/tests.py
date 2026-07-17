from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Category, Course


class CourseCreationTests(TestCase):
    """Tests for US-15 instructor course creation."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="course.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.other_instructor = User.objects.create_user(
            email="other.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="course.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Programming",
        )

        self.create_url = reverse(
            "courses:course_create"
        )

        self.list_url = reverse(
            "courses:instructor_course_list"
        )

        self.valid_data = {
            "title": "Python for Beginners",
            "category": self.category.pk,
            "description": (
                "Learn Python programming through "
                "practical examples and exercises."
            ),
            "level": Course.Level.BEGINNER,
            "price": "29.99",
            "learning_objectives": (
                "Understand Python syntax\n"
                "Use variables and data types\n"
                "Write reusable functions"
            ),
        }

    def test_course_creation_requires_login(self):
        response = self.client.get(self.create_url)

        expected_url = (
            reverse("accounts:login")
            + "?next="
            + self.create_url
        )

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_learner_cannot_open_course_creation_page(self):
        self.client.force_login(self.learner)

        response = self.client.get(self.create_url)

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
            fetch_redirect_response=False,
        )

    def test_instructor_can_open_course_creation_page(self):
        self.client.force_login(self.instructor)

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "courses/course_create.html",
        )

    def test_instructor_can_create_course(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.create_url,
            self.valid_data,
        )

        self.assertRedirects(
            response,
            self.list_url,
        )

        course = Course.objects.get(
            title="Python for Beginners"
        )

        self.assertEqual(
            course.instructor,
            self.instructor,
        )

        self.assertEqual(
            course.status,
            Course.Status.DRAFT,
        )

        self.assertEqual(
            str(course.price),
            "29.99",
        )

    def test_negative_price_is_rejected(self):
        self.client.force_login(self.instructor)

        invalid_data = self.valid_data.copy()
        invalid_data["price"] = "-10.00"

        response = self.client.post(
            self.create_url,
            invalid_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Course.objects.exists())
        self.assertTrue(
            response.context["form"].errors["price"]
        )

    def test_short_title_is_rejected(self):
        self.client.force_login(self.instructor)

        invalid_data = self.valid_data.copy()
        invalid_data["title"] = "AI"

        response = self.client.post(
            self.create_url,
            invalid_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Course.objects.exists())

        self.assertContains(
            response,
            "The course title must contain at least 5 characters.",
        )

    def test_instructor_only_sees_own_courses(self):
        Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="My Python Course",
            description="My course description.",
            level=Course.Level.BEGINNER,
            price="0.00",
            learning_objectives="Learn Python",
        )

        Course.objects.create(
            instructor=self.other_instructor,
            category=self.category,
            title="Another Instructor Course",
            description="Another course description.",
            level=Course.Level.INTERMEDIATE,
            price="10.00",
            learning_objectives="Learn another topic",
        )

        self.client.force_login(self.instructor)

        response = self.client.get(self.list_url)

        self.assertContains(
            response,
            "My Python Course",
        )

        self.assertNotContains(
            response,
            "Another Instructor Course",
        )