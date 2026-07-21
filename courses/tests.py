from django.test import TestCase
from django.urls import reverse
from .forms import CourseAdminReviewForm
from accounts.models import User
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

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
            "duration_minutes": "120",
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

class CourseApprovalTests(TestCase):
    """Tests for US-22 course approval workflow."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="approval.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.other_instructor = User.objects.create_user(
            email="approval.other@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="approval.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.admin_user = User.objects.create_superuser(
            email="approval.admin@example.com",
            password=self.password,
        )

        self.category = Category.objects.create(
            name="Programming",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Django Web Development",
            description=(
                "Learn how to build web applications "
                "using Django."
            ),
            level=Course.Level.INTERMEDIATE,
            price="39.99",
            learning_objectives=(
                "Understand Django models\n"
                "Create views and templates"
            ),
            status=Course.Status.DRAFT,
        )

        self.submit_url = reverse(
            "courses:course_submit",
            args=[self.course.pk],
        )

        self.admin_list_url = reverse(
            "admin:courses_course_changelist"
        )

    def test_instructor_can_submit_own_course(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.submit_url
        )

        self.assertRedirects(
            response,
            reverse("courses:instructor_course_list"),
        )

        self.course.refresh_from_db()

        self.assertEqual(
            self.course.status,
            Course.Status.SUBMITTED,
        )

    def test_learner_cannot_submit_course(self):
        self.client.force_login(self.learner)

        response = self.client.post(
            self.submit_url
        )

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
            fetch_redirect_response=False,
        )

        self.course.refresh_from_db()

        self.assertEqual(
            self.course.status,
            Course.Status.DRAFT,
        )

    def test_instructor_cannot_submit_another_course(self):
        self.client.force_login(
            self.other_instructor
        )

        response = self.client.post(
            self.submit_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.course.refresh_from_db()

        self.assertEqual(
            self.course.status,
            Course.Status.DRAFT,
        )

    def test_course_submission_requires_post(self):
        self.client.force_login(self.instructor)

        response = self.client.get(
            self.submit_url
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_admin_can_approve_submitted_course(self):
        self.course.status = Course.Status.SUBMITTED
        self.course.save()

        self.client.force_login(
            self.admin_user
        )

        response = self.client.post(
            self.admin_list_url,
            {
                "action": "approve_submitted_courses",
                "_selected_action": [
                    str(self.course.pk)
                ],
                "select_across": "0",
                "index": "0",
            },
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.course.refresh_from_db()

        self.assertEqual(
            self.course.status,
            Course.Status.APPROVED,
        )

        self.assertEqual(
            self.course.rejection_reason,
            "",
        )

    def test_admin_can_reject_submitted_course(self):
        self.course.status = Course.Status.SUBMITTED
        self.course.save()

        self.client.force_login(
            self.admin_user
        )

        response = self.client.post(
            self.admin_list_url,
            {
                "action": "reject_submitted_courses",
                "_selected_action": [
                    str(self.course.pk)
                ],
                "select_across": "0",
                "index": "0",
            },
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.course.refresh_from_db()

        self.assertEqual(
            self.course.status,
            Course.Status.REJECTED,
        )

        self.assertTrue(
            self.course.rejection_reason
        )

    def test_rejection_requires_reason(self):
        form = CourseAdminReviewForm(
            instance=self.course,
            data={
                "instructor": self.instructor.pk,
                "category": self.category.pk,
                "title": self.course.title,
                "description": self.course.description,
                "level": self.course.level,
                "price": self.course.price,
                "learning_objectives": (
                    self.course.learning_objectives
                ),
                "status": Course.Status.REJECTED,
                "rejection_reason": "",
            },
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "rejection_reason",
            form.errors,
        )

class CourseCatalogTests(TestCase):
    """Tests for US-04 browsing available courses."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="catalog.instructor@example.com",
            password=self.password,
            first_name="Course",
            last_name="Instructor",
            role=User.Role.INSTRUCTOR,
        )

        self.category = Category.objects.create(
            name="Data Science",
        )

        self.approved_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Approved Python Course",
            description=(
                "An approved course that learners should see."
            ),
            level=Course.Level.BEGINNER,
            price="19.99",
            learning_objectives="Learn Python",
            status=Course.Status.APPROVED,
        )

        self.draft_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Hidden Draft Course",
            description="This draft should remain hidden.",
            level=Course.Level.BEGINNER,
            price="0.00",
            learning_objectives="Draft objective",
            status=Course.Status.DRAFT,
        )

        self.submitted_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Hidden Submitted Course",
            description="This submitted course should remain hidden.",
            level=Course.Level.INTERMEDIATE,
            price="10.00",
            learning_objectives="Submitted objective",
            status=Course.Status.SUBMITTED,
        )

        self.rejected_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Hidden Rejected Course",
            description="This rejected course should remain hidden.",
            level=Course.Level.ADVANCED,
            price="25.00",
            learning_objectives="Rejected objective",
            status=Course.Status.REJECTED,
            rejection_reason="More detail is required.",
        )

        self.catalog_url = reverse(
            "courses:course_catalog"
        )

    def test_catalog_page_opens(self):
        response = self.client.get(
            self.catalog_url
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "courses/course_catalog.html",
        )

    def test_approved_course_is_displayed(self):
        response = self.client.get(
            self.catalog_url
        )

        self.assertContains(
            response,
            "Approved Python Course",
        )

    def test_draft_course_is_hidden(self):
        response = self.client.get(
            self.catalog_url
        )

        self.assertNotContains(
            response,
            "Hidden Draft Course",
        )

    def test_submitted_course_is_hidden(self):
        response = self.client.get(
            self.catalog_url
        )

        self.assertNotContains(
            response,
            "Hidden Submitted Course",
        )

    def test_rejected_course_is_hidden(self):
        response = self.client.get(
            self.catalog_url
        )

        self.assertNotContains(
            response,
            "Hidden Rejected Course",
        )

    def test_catalog_displays_course_information(self):
        response = self.client.get(
            self.catalog_url
        )

        self.assertContains(
            response,
            "Data Science",
        )

        self.assertContains(
            response,
            "Beginner",
        )

        self.assertContains(
            response,
            "€19.99",
        )

        self.assertContains(
            response,
            "Course Instructor",
        )

    def test_catalog_uses_pagination(self):
        for number in range(10):
            Course.objects.create(
                instructor=self.instructor,
                category=self.category,
                title=f"Approved Course {number}",
                description="Approved catalog course.",
                level=Course.Level.BEGINNER,
                price="0.00",
                learning_objectives="Learn a topic",
                status=Course.Status.APPROVED,
            )

        response = self.client.get(
            self.catalog_url
        )

        self.assertTrue(
            response.context["page_obj"].has_next()
        )

        self.assertEqual(
            len(response.context["page_obj"]),
            9,
        )

class CourseDetailTests(TestCase):
    """Tests for US-07 course details."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="details.instructor@example.com",
            password=self.password,
            first_name="Yasser",
            last_name="Instructor",
            role=User.Role.INSTRUCTOR,
        )

        self.category = Category.objects.create(
            name="Programming",
        )

        self.approved_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Complete Django Course",
            description=(
                "Learn Django by developing complete "
                "web applications."
            ),
            level=Course.Level.INTERMEDIATE,
            price="39.99",
            duration_minutes=150,
            learning_objectives=(
                "Understand Django models\n"
                "Create views and templates\n"
                "Build secure authentication"
            ),
            status=Course.Status.APPROVED,
        )

        self.draft_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Hidden Draft Details",
            description="This course is still a draft.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=60,
            learning_objectives="Learn a draft topic",
            status=Course.Status.DRAFT,
        )

        self.detail_url = reverse(
            "courses:course_detail",
            args=[self.approved_course.pk],
        )

    def test_approved_course_detail_page_opens(self):
        response = self.client.get(
            self.detail_url
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "courses/course_detail.html",
        )

    def test_course_details_are_displayed(self):
        response = self.client.get(
            self.detail_url
        )

        self.assertContains(
            response,
            "Complete Django Course",
        )

        self.assertContains(
            response,
            "Yasser Instructor",
        )

        self.assertContains(
            response,
            "Programming",
        )

        self.assertContains(
            response,
            "Intermediate",
        )

        self.assertContains(
            response,
            "€39.99",
        )

        self.assertContains(
            response,
            "2 hr 30 min",
        )

        self.assertContains(
            response,
            "Understand Django models",
        )

    def test_draft_course_detail_is_hidden(self):
        hidden_url = reverse(
            "courses:course_detail",
            args=[self.draft_course.pk],
        )

        response = self.client.get(
            hidden_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_nonexistent_course_returns_404(self):
        missing_url = reverse(
            "courses:course_detail",
            args=[99999],
        )

        response = self.client.get(
            missing_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_catalog_links_to_course_details(self):
        response = self.client.get(
            reverse("courses:course_catalog")
        )

        self.assertContains(
            response,
            self.detail_url,
        )

TEST_VIDEO_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_VIDEO_MEDIA_ROOT)
class CourseVideoUploadTests(TestCase):
    """Tests for US-16 course video uploads."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(
            TEST_VIDEO_MEDIA_ROOT,
            ignore_errors=True,
        )

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="video.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.other_instructor = User.objects.create_user(
            email="video.other@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="video.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Video Programming",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Python Video Course",
            description="A course containing video lessons.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=120,
            learning_objectives="Learn Python",
            status=Course.Status.DRAFT,
        )

        self.other_course = Course.objects.create(
            instructor=self.other_instructor,
            category=self.category,
            title="Other Instructor Course",
            description="Another instructor's course.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=60,
            learning_objectives="Learn another subject",
            status=Course.Status.DRAFT,
        )

        self.section = CourseSection.objects.create(
            course=self.course,
            title="Python Basics",
            order=1,
        )

        self.content_url = reverse(
            "courses:course_content_manage",
            args=[self.course.pk],
        )

        self.section_url = reverse(
            "courses:course_section_create",
            args=[self.course.pk],
        )

        self.upload_url = reverse(
            "courses:video_lesson_upload",
            args=[self.course.pk],
        )

    def create_video_file(
        self,
        name="lesson.mp4",
    ):
        return SimpleUploadedFile(
            name=name,
            content=b"fake video file content",
            content_type="video/mp4",
        )

    def test_instructor_can_open_course_content_page(self):
        self.client.force_login(self.instructor)

        response = self.client.get(
            self.content_url
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "courses/course_content_manage.html",
        )

    def test_learner_cannot_manage_course_content(self):
        self.client.force_login(self.learner)

        response = self.client.get(
            self.content_url
        )

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
            fetch_redirect_response=False,
        )

    def test_instructor_cannot_manage_another_course(self):
        self.client.force_login(self.instructor)

        other_url = reverse(
            "courses:course_content_manage",
            args=[self.other_course.pk],
        )

        response = self.client.get(other_url)

        self.assertEqual(response.status_code, 404)

    def test_instructor_can_create_section(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.section_url,
            {
                "title": "Control Flow",
                "order": 2,
            },
        )

        self.assertRedirects(
            response,
            self.content_url,
        )

        self.assertTrue(
            CourseSection.objects.filter(
                course=self.course,
                title="Control Flow",
                order=2,
            ).exists()
        )

    def test_instructor_can_upload_video_lesson(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.upload_url,
            {
                "section": self.section.pk,
                "title": "Installing Python",
                "video_file": self.create_video_file(),
                "order": 1,
                "duration_minutes": 10,
                "is_preview": "on",
            },
        )

        self.assertRedirects(
            response,
            self.content_url,
        )

        lesson = VideoLesson.objects.get(
            title="Installing Python"
        )

        self.assertEqual(
            lesson.section,
            self.section,
        )

        self.assertTrue(lesson.is_preview)
        self.assertTrue(bool(lesson.video_file))

    def test_invalid_video_extension_is_rejected(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.upload_url,
            {
                "section": self.section.pk,
                "title": "Invalid Lesson",
                "video_file": self.create_video_file(
                    name="malicious.exe"
                ),
                "order": 1,
                "duration_minutes": 10,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(VideoLesson.objects.exists())

    def test_duplicate_lesson_order_is_rejected(self):
        VideoLesson.objects.create(
            section=self.section,
            title="Existing Lesson",
            video_file=self.create_video_file(
                name="existing.mp4"
            ),
            order=1,
            duration_minutes=10,
        )

        self.client.force_login(self.instructor)

        response = self.client.post(
            self.upload_url,
            {
                "section": self.section.pk,
                "title": "Duplicate Order Lesson",
                "video_file": self.create_video_file(
                    name="duplicate.mp4"
                ),
                "order": 1,
                "duration_minutes": 15,
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Another lesson already uses this order number.",
        )

        self.assertEqual(
            VideoLesson.objects.count(),
            1,
        )

class CourseSearchTests(TestCase):
    """Tests for US-05 course keyword search."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="john.teacher@example.com",
            password=self.password,
            first_name="John",
            last_name="Teacher",
            role=User.Role.INSTRUCTOR,
        )

        self.programming_category = Category.objects.create(
            name="Programming Search",
        )

        self.business_category = Category.objects.create(
            name="Business Search",
        )

        self.python_course = Course.objects.create(
            instructor=self.instructor,
            category=self.programming_category,
            title="Python Programming Fundamentals",
            description=(
                "Learn variables, functions and object-oriented "
                "programming."
            ),
            level=Course.Level.BEGINNER,
            price="19.99",
            duration_minutes=120,
            learning_objectives="Learn Python fundamentals",
            status=Course.Status.APPROVED,
        )

        self.marketing_course = Course.objects.create(
            instructor=self.instructor,
            category=self.business_category,
            title="Digital Marketing Strategy",
            description=(
                "Learn online campaigns and customer engagement."
            ),
            level=Course.Level.INTERMEDIATE,
            price="29.99",
            duration_minutes=90,
            learning_objectives="Create marketing campaigns",
            status=Course.Status.APPROVED,
        )

        self.hidden_course = Course.objects.create(
            instructor=self.instructor,
            category=self.programming_category,
            title="Hidden Python Advanced Course",
            description="This draft course must remain hidden.",
            level=Course.Level.ADVANCED,
            price="49.99",
            duration_minutes=180,
            learning_objectives="Learn advanced Python",
            status=Course.Status.DRAFT,
        )

        self.catalog_url = reverse(
            "courses:course_catalog"
        )

    def test_search_by_course_title(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "Python",
            },
        )

        self.assertContains(
            response,
            "Python Programming Fundamentals",
        )

        self.assertNotContains(
            response,
            "Digital Marketing Strategy",
        )

    def test_search_is_case_insensitive(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "python",
            },
        )

        self.assertContains(
            response,
            "Python Programming Fundamentals",
        )

    def test_search_by_description(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "customer engagement",
            },
        )

        self.assertContains(
            response,
            "Digital Marketing Strategy",
        )

    def test_search_by_category(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "Business Search",
            },
        )

        self.assertContains(
            response,
            "Digital Marketing Strategy",
        )

        self.assertNotContains(
            response,
            "Python Programming Fundamentals",
        )

    def test_search_by_instructor_name(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "John",
            },
        )

        self.assertContains(
            response,
            "Python Programming Fundamentals",
        )

        self.assertContains(
            response,
            "Digital Marketing Strategy",
        )

        self.assertContains(
            response,
            "Python Programming Fundamentals",
        )

        self.assertContains(
            response,
            "Digital Marketing Strategy",
        )

    def test_search_hides_non_approved_courses(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "Hidden Python",
            },
        )

        self.assertNotContains(
            response,
            "Hidden Python Advanced Course",
        )

        self.assertContains(
            response,
            "No matching courses found",
        )

    def test_no_results_message_is_displayed(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "Cybersecurity",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "No matching courses found",
        )

        self.assertContains(
            response,
            "Cybersecurity",
        )

    def test_search_query_is_kept_in_context(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "Python",
            },
        )

        self.assertEqual(
            response.context["query"],
            "Python",
        )

        self.assertEqual(
            response.context["result_count"],
            1,
        )

class CourseEnrollmentTests(TestCase):
    """Tests for US-06 learner course enrollment."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="enrollment.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="enrollment.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Enrollment Programming",
        )

        self.approved_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Approved Enrollment Course",
            description="An approved course open for enrollment.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=120,
            learning_objectives="Learn enrollment testing",
            status=Course.Status.APPROVED,
        )

        self.draft_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Draft Enrollment Course",
            description="A draft course that cannot accept learners.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=60,
            learning_objectives="Hidden enrollment objective",
            status=Course.Status.DRAFT,
        )

        self.detail_url = reverse(
            "courses:course_detail",
            args=[self.approved_course.pk],
        )

        self.enroll_url = reverse(
            "courses:course_enroll",
            args=[self.approved_course.pk],
        )

    def test_enrollment_requires_login(self):
        response = self.client.post(
            self.enroll_url
        )

        expected_url = (
            reverse("accounts:login")
            + "?next="
            + self.enroll_url
        )

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_learner_can_enroll_in_approved_course(self):
        self.client.force_login(self.learner)

        response = self.client.post(
            self.enroll_url
        )

        self.assertRedirects(
            response,
            self.detail_url,
        )

        self.assertTrue(
            Enrollment.objects.filter(
                learner=self.learner,
                course=self.approved_course,
            ).exists()
        )

    def test_duplicate_enrollment_is_not_created(self):
        Enrollment.objects.create(
            learner=self.learner,
            course=self.approved_course,
        )

        self.client.force_login(self.learner)

        response = self.client.post(
            self.enroll_url
        )

        self.assertRedirects(
            response,
            self.detail_url,
        )

        self.assertEqual(
            Enrollment.objects.filter(
                learner=self.learner,
                course=self.approved_course,
            ).count(),
            1,
        )

    def test_instructor_cannot_enroll(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.enroll_url
        )

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
            fetch_redirect_response=False,
        )

        self.assertFalse(
            Enrollment.objects.exists()
        )

    def test_learner_cannot_enroll_in_draft_course(self):
        hidden_enroll_url = reverse(
            "courses:course_enroll",
            args=[self.draft_course.pk],
        )

        self.client.force_login(self.learner)

        response = self.client.post(
            hidden_enroll_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            Enrollment.objects.exists()
        )

    def test_enrollment_requires_post(self):
        self.client.force_login(self.learner)

        response = self.client.get(
            self.enroll_url
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_detail_page_shows_enroll_button(self):
        self.client.force_login(self.learner)

        response = self.client.get(
            self.detail_url
        )

        self.assertContains(
            response,
            "Enroll for free",
        )

    def test_detail_page_shows_enrolled_status(self):
        Enrollment.objects.create(
            learner=self.learner,
            course=self.approved_course,
        )

        self.client.force_login(self.learner)

        response = self.client.get(
            self.detail_url
        )

        self.assertContains(
            response,
            "You are enrolled in this course.",
        )

        self.assertNotContains(
            response,
            "Enroll now",
        )

class CourseFilterTests(TestCase):
    """Tests for filtering courses by category and level."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="filter.instructor@example.com",
            password=self.password,
            first_name="Filter",
            last_name="Instructor",
            role=User.Role.INSTRUCTOR,
        )

        self.programming = Category.objects.create(
            name="Filter Programming",
        )

        self.business = Category.objects.create(
            name="Filter Business",
        )

        self.beginner_python = Course.objects.create(
            instructor=self.instructor,
            category=self.programming,
            title="Beginner Python Filtering",
            description="A beginner programming course.",
            level=Course.Level.BEGINNER,
            price="10.00",
            duration_minutes=90,
            learning_objectives="Learn beginner Python",
            status=Course.Status.APPROVED,
        )

        self.advanced_python = Course.objects.create(
            instructor=self.instructor,
            category=self.programming,
            title="Advanced Python Filtering",
            description="An advanced programming course.",
            level=Course.Level.ADVANCED,
            price="30.00",
            duration_minutes=180,
            learning_objectives="Learn advanced Python",
            status=Course.Status.APPROVED,
        )

        self.beginner_business = Course.objects.create(
            instructor=self.instructor,
            category=self.business,
            title="Beginner Business Filtering",
            description="A beginner business course.",
            level=Course.Level.BEGINNER,
            price="15.00",
            duration_minutes=60,
            learning_objectives="Learn business fundamentals",
            status=Course.Status.APPROVED,
        )

        self.hidden_draft = Course.objects.create(
            instructor=self.instructor,
            category=self.business,
            title="Hidden Draft Business Course",
            description="This draft must remain hidden.",
            level=Course.Level.ADVANCED,
            price="20.00",
            duration_minutes=80,
            learning_objectives="Hidden objective",
            status=Course.Status.DRAFT,
        )

        self.catalog_url = reverse(
            "courses:course_catalog"
        )

    def test_filter_by_category(self):
        response = self.client.get(
            self.catalog_url,
            {
                "category": self.programming.pk,
            },
        )

        self.assertContains(
            response,
            "Beginner Python Filtering",
        )

        self.assertContains(
            response,
            "Advanced Python Filtering",
        )

        self.assertNotContains(
            response,
            "Beginner Business Filtering",
        )

    def test_filter_by_level(self):
        response = self.client.get(
            self.catalog_url,
            {
                "level": Course.Level.BEGINNER,
            },
        )

        self.assertContains(
            response,
            "Beginner Python Filtering",
        )

        self.assertContains(
            response,
            "Beginner Business Filtering",
        )

        self.assertNotContains(
            response,
            "Advanced Python Filtering",
        )

    def test_filter_by_category_and_level(self):
        response = self.client.get(
            self.catalog_url,
            {
                "category": self.programming.pk,
                "level": Course.Level.ADVANCED,
            },
        )

        self.assertContains(
            response,
            "Advanced Python Filtering",
        )

        self.assertNotContains(
            response,
            "Beginner Python Filtering",
        )

        self.assertNotContains(
            response,
            "Beginner Business Filtering",
        )

    def test_search_and_filters_work_together(self):
        response = self.client.get(
            self.catalog_url,
            {
                "q": "Python",
                "category": self.programming.pk,
                "level": Course.Level.BEGINNER,
            },
        )

        self.assertContains(
            response,
            "Beginner Python Filtering",
        )

        self.assertNotContains(
            response,
            "Advanced Python Filtering",
        )

        self.assertNotContains(
            response,
            "Beginner Business Filtering",
        )

    def test_draft_courses_remain_hidden(self):
        response = self.client.get(
            self.catalog_url,
            {
                "category": self.business.pk,
                "level": Course.Level.ADVANCED,
            },
        )

        self.assertNotContains(
            response,
            "Hidden Draft Business Course",
        )

        self.assertContains(
            response,
            "No matching courses found",
        )

    def test_selected_filters_are_kept_in_context(self):
        response = self.client.get(
            self.catalog_url,
            {
                "category": self.programming.pk,
                "level": Course.Level.ADVANCED,
            },
        )

        self.assertEqual(
            response.context["selected_category_id"],
            self.programming.pk,
        )

        self.assertEqual(
            response.context["selected_level"],
            Course.Level.ADVANCED,
        )

    def test_invalid_filters_do_not_crash_page(self):
        response = self.client.get(
            self.catalog_url,
            {
                "category": "invalid",
                "level": "INVALID_LEVEL",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Beginner Python Filtering",
        )

        self.assertContains(
            response,
            "Advanced Python Filtering",
        )

class CoursePurchaseTests(TestCase):
    """Tests for the simulated course-purchase workflow."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="purchase.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="purchase.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Purchase Testing",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Paid Django Course",
            description="A paid course used for testing purchases.",
            level=Course.Level.BEGINNER,
            price="29.99",
            duration_minutes=120,
            learning_objectives="Learn Django",
            status=Course.Status.APPROVED,
        )

        self.purchase_url = reverse(
            "courses:course_purchase",
            args=[self.course.pk],
        )

    def test_learner_can_purchase_course(self):
        self.client.force_login(self.learner)

        response = self.client.post(
            self.purchase_url
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:course_detail",
                args=[self.course.pk],
            ),
        )

        self.assertTrue(
            PaymentTransaction.objects.filter(
                learner=self.learner,
                course=self.course,
                status=PaymentTransaction.Status.SUCCESSFUL,
            ).exists()
        )

        self.assertTrue(
            Enrollment.objects.filter(
                learner=self.learner,
                course=self.course,
            ).exists()
        )

    def test_duplicate_purchase_is_not_created(self):
        self.client.force_login(self.learner)

        self.client.post(self.purchase_url)
        self.client.post(self.purchase_url)

        self.assertEqual(
            PaymentTransaction.objects.filter(
                learner=self.learner,
                course=self.course,
                status=PaymentTransaction.Status.SUCCESSFUL,
            ).count(),
            1,
        )

        self.assertEqual(
            Enrollment.objects.filter(
                learner=self.learner,
                course=self.course,
            ).count(),
            1,
        )

    def test_instructor_cannot_purchase_course(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.purchase_url
        )

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
            fetch_redirect_response=False,
        )

        self.assertFalse(
            PaymentTransaction.objects.exists()
        )
        
class WatchCourseVideoTests(TestCase):
    """Tests for watching enrolled course videos."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="watch.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="watch.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.other_learner = User.objects.create_user(
            email="watch.other@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Video Watching",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Watch Python Videos",
            description="A course containing video lessons.",
            level=Course.Level.BEGINNER,
            price="20.00",
            duration_minutes=60,
            learning_objectives="Watch Python lessons",
            status=Course.Status.APPROVED,
        )

        self.section = CourseSection.objects.create(
            course=self.course,
            title="Python Basics",
            order=1,
        )

        self.lesson = VideoLesson.objects.create(
            section=self.section,
            title="Python Introduction",
            video_file="courses/tests/python-introduction.mp4",
            order=1,
            duration_minutes=10,
        )

        Enrollment.objects.create(
            learner=self.learner,
            course=self.course,
        )

        self.content_url = reverse(
            "courses:learner_course_content",
            args=[self.course.pk],
        )

        self.lesson_url = reverse(
            "courses:lesson_watch",
            args=[self.lesson.pk],
        )

    def test_enrolled_learner_can_view_course_content(self):
        self.client.force_login(self.learner)

        response = self.client.get(self.content_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")
        self.assertContains(response, "Python Introduction")

    def test_enrolled_learner_can_watch_video(self):
        self.client.force_login(self.learner)

        response = self.client.get(self.lesson_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Introduction")
        self.assertContains(
            response,
            self.lesson.video_file.url,
        )

    def test_non_enrolled_learner_cannot_watch_video(self):
        self.client.force_login(self.other_learner)

        response = self.client.get(self.lesson_url)

        self.assertEqual(response.status_code, 404)


class CourseReviewTests(TestCase):
    """Tests for course ratings and reviews."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="review.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="review.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.other_learner = User.objects.create_user(
            email="review.other@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Review Testing",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Reviewed Django Course",
            description="A course used for review testing.",
            level=Course.Level.BEGINNER,
            price="10.00",
            duration_minutes=60,
            learning_objectives="Learn Django",
            status=Course.Status.APPROVED,
        )

        Enrollment.objects.create(
            learner=self.learner,
            course=self.course,
        )

        self.review_url = reverse(
            "courses:course_review_submit",
            args=[self.course.pk],
        )

    def test_enrolled_learner_can_review_course(self):
        self.client.force_login(self.learner)

        response = self.client.post(
            self.review_url,
            {
                "rating": 5,
                "comment": "Excellent course.",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:course_detail",
                args=[self.course.pk],
            ),
        )

        self.assertTrue(
            CourseReview.objects.filter(
                learner=self.learner,
                course=self.course,
                rating=5,
            ).exists()
        )

    def test_non_enrolled_learner_cannot_review(self):
        self.client.force_login(self.other_learner)

        response = self.client.post(
            self.review_url,
            {
                "rating": 4,
                "comment": "Unauthorized review.",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(CourseReview.objects.count(), 0)

    def test_second_submission_updates_existing_review(self):
        CourseReview.objects.create(
            learner=self.learner,
            course=self.course,
            rating=3,
            comment="Good.",
        )

        self.client.force_login(self.learner)

        self.client.post(
            self.review_url,
            {
                "rating": 5,
                "comment": "Excellent after completing it.",
            },
        )

        self.assertEqual(
            CourseReview.objects.filter(
                learner=self.learner,
                course=self.course,
            ).count(),
            1,
        )

        review = CourseReview.objects.get(
            learner=self.learner,
            course=self.course,
        )

        self.assertEqual(review.rating, 5)

class InstructorQuizTests(TestCase):
    """Tests for creating and publishing course quizzes."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="quiz.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.other_instructor = User.objects.create_user(
            email="quiz.other@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.category = Category.objects.create(
            name="Quiz Testing",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Quiz Django Course",
            description="A course containing quizzes.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=60,
            learning_objectives="Complete quizzes",
            status=Course.Status.APPROVED,
        )

        self.create_url = reverse(
            "courses:quiz_create",
            args=[self.course.pk],
        )

    def test_instructor_can_create_quiz(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.create_url,
            {
                "title": "Final Quiz",
                "description": "Test your course knowledge.",
                "passing_score": 60,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:instructor_quiz_list",
                args=[self.course.pk],
            ),
        )

        self.assertTrue(
            Quiz.objects.filter(
                course=self.course,
                title="Final Quiz",
            ).exists()
        )

    def test_instructor_can_add_question(self):
        quiz = Quiz.objects.create(
            course=self.course,
            title="Python Quiz",
            passing_score=60,
        )

        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse(
                "courses:quiz_question_create",
                args=[self.course.pk, quiz.pk],
            ),
            {
                "text": "Which keyword creates a function?",
                "option_a": "class",
                "option_b": "def",
                "option_c": "return",
                "option_d": "import",
                "correct_option": "B",
                "order": 1,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:instructor_quiz_list",
                args=[self.course.pk],
            ),
        )

        self.assertEqual(
            QuizQuestion.objects.filter(
                quiz=quiz,
            ).count(),
            1,
        )

    def test_quiz_with_question_can_be_published(self):
        quiz = Quiz.objects.create(
            course=self.course,
            title="Publishable Quiz",
            passing_score=60,
        )

        QuizQuestion.objects.create(
            quiz=quiz,
            text="What framework is this project using?",
            option_a="Flask",
            option_b="Laravel",
            option_c="Django",
            option_d="Spring",
            correct_option="C",
            order=1,
        )

        self.client.force_login(self.instructor)

        self.client.post(
            reverse(
                "courses:quiz_publish",
                args=[self.course.pk, quiz.pk],
            )
        )

        quiz.refresh_from_db()

        self.assertTrue(quiz.is_published)

    def test_other_instructor_cannot_manage_quiz(self):
        self.client.force_login(self.other_instructor)

        response = self.client.get(
            self.create_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class CompleteCourseQuizTests(TestCase):
    """Tests for learner quiz completion and scoring."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="complete.quiz.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="complete.quiz.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.other_learner = User.objects.create_user(
            email="complete.quiz.other@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Quiz Completion Testing",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Complete Python Quiz",
            description="A course used for quiz completion tests.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=60,
            learning_objectives="Complete the quiz",
            status=Course.Status.APPROVED,
        )

        Enrollment.objects.create(
            learner=self.learner,
            course=self.course,
        )

        self.quiz = Quiz.objects.create(
            course=self.course,
            title="Python Final Quiz",
            description="Complete all questions.",
            passing_score=60,
            is_published=True,
        )

        self.question_one = QuizQuestion.objects.create(
            quiz=self.quiz,
            text="Which keyword creates a Python function?",
            option_a="class",
            option_b="def",
            option_c="import",
            option_d="return",
            correct_option="B",
            order=1,
        )

        self.question_two = QuizQuestion.objects.create(
            quiz=self.quiz,
            text="Which value is a Boolean?",
            option_a="True",
            option_b="Python",
            option_c="10.5",
            option_d="Hello",
            correct_option="A",
            order=2,
        )

        self.quiz_url = reverse(
            "courses:quiz_take",
            args=[self.quiz.pk],
        )

    def test_enrolled_learner_can_open_published_quiz(self):
        self.client.force_login(self.learner)

        response = self.client.get(
            self.quiz_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Python Final Quiz",
        )

        self.assertContains(
            response,
            self.question_one.text,
        )

    def test_learner_can_submit_quiz_and_pass(self):
        self.client.force_login(self.learner)

        response = self.client.post(
            self.quiz_url,
            {
                f"question_{self.question_one.pk}": "B",
                f"question_{self.question_two.pk}": "A",
            },
        )

        attempt = QuizAttempt.objects.get(
            learner=self.learner,
            quiz=self.quiz,
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:quiz_result",
                args=[attempt.pk],
            ),
        )

        self.assertEqual(
            attempt.score,
            100,
        )

        self.assertEqual(
            attempt.correct_answers,
            2,
        )

        self.assertTrue(
            attempt.passed,
        )

        self.assertEqual(
            QuizAnswer.objects.filter(
                attempt=attempt,
            ).count(),
            2,
        )

    def test_quiz_score_and_failed_result_are_calculated(self):
        self.client.force_login(self.learner)

        self.client.post(
            self.quiz_url,
            {
                f"question_{self.question_one.pk}": "B",
                f"question_{self.question_two.pk}": "D",
            },
        )

        attempt = QuizAttempt.objects.get(
            learner=self.learner,
            quiz=self.quiz,
        )

        self.assertEqual(
            attempt.score,
            50,
        )

        self.assertEqual(
            attempt.correct_answers,
            1,
        )

        self.assertFalse(
            attempt.passed,
        )

    def test_missing_answer_does_not_create_attempt(self):
        self.client.force_login(self.learner)

        response = self.client.post(
            self.quiz_url,
            {
                f"question_{self.question_one.pk}": "B",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Select one answer for this question.",
        )

        self.assertFalse(
            QuizAttempt.objects.exists(),
        )

    def test_non_enrolled_learner_cannot_open_quiz(self):
        self.client.force_login(
            self.other_learner
        )

        response = self.client.get(
            self.quiz_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

class CourseCertificateTests(TestCase):
    """Tests for generating and downloading course certificates."""

    def setUp(self):
        self.password = "Mango7!River#Cloud92"

        self.instructor = User.objects.create_user(
            email="certificate.instructor@example.com",
            password=self.password,
            role=User.Role.INSTRUCTOR,
        )

        self.learner = User.objects.create_user(
            email="certificate.learner@example.com",
            password=self.password,
            role=User.Role.LEARNER,
            first_name="Certificate",
            last_name="Learner",
        )

        self.other_learner = User.objects.create_user(
            email="certificate.other@example.com",
            password=self.password,
            role=User.Role.LEARNER,
        )

        self.category = Category.objects.create(
            name="Certificate Testing",
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Certificate Django Course",
            description="Course used for certificate testing.",
            level=Course.Level.BEGINNER,
            price="0.00",
            duration_minutes=60,
            learning_objectives="Earn a certificate",
            status=Course.Status.APPROVED,
        )

        Enrollment.objects.create(
            learner=self.learner,
            course=self.course,
        )

        self.quiz = Quiz.objects.create(
            course=self.course,
            title="Certificate Final Quiz",
            description="Pass to unlock the certificate.",
            passing_score=60,
            is_published=True,
        )

        self.question = QuizQuestion.objects.create(
            quiz=self.quiz,
            text="Which framework is SkillHub using?",
            option_a="Flask",
            option_b="Django",
            option_c="Laravel",
            option_d="Spring",
            correct_option="B",
            order=1,
        )

        self.download_url = reverse(
            "courses:certificate_download",
            args=[self.course.pk],
        )

    def create_passed_attempt(self):
        return QuizAttempt.objects.create(
            learner=self.learner,
            quiz=self.quiz,
            score=100,
            total_questions=1,
            correct_answers=1,
            passed=True,
        )

    def test_learner_must_pass_quiz_before_download(self):
        self.client.force_login(self.learner)

        response = self.client.get(
            self.download_url
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:learner_course_content",
                args=[self.course.pk],
            ),
        )

        self.assertFalse(
            Certificate.objects.exists()
        )

    def test_completed_learner_can_download_pdf(self):
        self.create_passed_attempt()

        self.client.force_login(self.learner)

        response = self.client.get(
            self.download_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "application/pdf",
        )

        self.assertIn(
            "attachment;",
            response["Content-Disposition"],
        )

        self.assertTrue(
            response.content.startswith(b"%PDF")
        )

        self.assertTrue(
            Certificate.objects.filter(
                learner=self.learner,
                course=self.course,
            ).exists()
        )

    def test_downloading_twice_does_not_duplicate_certificate(self):
        self.create_passed_attempt()

        self.client.force_login(self.learner)

        self.client.get(self.download_url)
        self.client.get(self.download_url)

        self.assertEqual(
            Certificate.objects.filter(
                learner=self.learner,
                course=self.course,
            ).count(),
            1,
        )

    def test_non_enrolled_learner_cannot_download_certificate(self):
        self.client.force_login(
            self.other_learner
        )

        response = self.client.get(
            self.download_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )