from decimal import Decimal

from django import forms

from .models import Course, CourseSection, VideoLesson

class CourseCreationForm(forms.ModelForm):
    """Form used by instructors to create draft courses."""

    class Meta:
        model = Course
        fields = (
            "title",
            "category",
            "description",
            "level",
            "price",
            "duration_minutes",
            "learning_objectives",
        )

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter the course title",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe the course content",
                }
            ),
            "level": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),
            "duration_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "For example: 120",
                }
            ),

            "learning_objectives": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Enter one learning objective per line"
                    ),
                }
            ),
        }

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if len(title) < 5:
            raise forms.ValidationError(
                "The course title must contain at least 5 characters."
            )

        return title

    def clean_price(self):
        price = self.cleaned_data.get("price")

        if price is None:
            return Decimal("0.00")

        if price < 0:
            raise forms.ValidationError(
                "The course price cannot be negative."
            )

        return price

    def clean_learning_objectives(self):
        objectives = self.cleaned_data[
            "learning_objectives"
        ].strip()

        objective_lines = [
            line.strip()
            for line in objectives.splitlines()
            if line.strip()
        ]

        if not objective_lines:
            raise forms.ValidationError(
                "Enter at least one learning objective."
            )

        return "\n".join(objective_lines)
    
class CourseAdminReviewForm(forms.ModelForm):
    """Validate course approval and rejection in Django Admin."""

    class Meta:
        model = Course
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        status = cleaned_data.get("status")
        rejection_reason = (
            cleaned_data.get("rejection_reason") or ""
        ).strip()

        if (
            status == Course.Status.REJECTED
            and not rejection_reason
        ):
            self.add_error(
                "rejection_reason",
                "A rejection reason is required.",
            )

        if status != Course.Status.REJECTED:
            cleaned_data["rejection_reason"] = ""

        return cleaned_data
    
class CourseSectionForm(forms.ModelForm):
    """Allow an instructor to add a section to a course."""

    class Meta:
        model = CourseSection
        fields = (
            "title",
            "order",
        )

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example: Python Basics",
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                }
            ),
        }

    def __init__(self, *args, course, **kwargs):
        self.course = course
        super().__init__(*args, **kwargs)

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if len(title) < 3:
            raise forms.ValidationError(
                "The section title must contain at least 3 characters."
            )

        return title

    def clean_order(self):
        order = self.cleaned_data["order"]

        duplicate_exists = CourseSection.objects.filter(
            course=self.course,
            order=order,
        ).exists()

        if duplicate_exists:
            raise forms.ValidationError(
                "Another section already uses this order number."
            )

        return order

    def save(self, commit=True):
        section = super().save(commit=False)
        section.course = self.course

        if commit:
            section.save()

        return section


class VideoLessonUploadForm(forms.ModelForm):
    """Allow instructors to upload and organize video lessons."""

    maximum_file_size = 200 * 1024 * 1024

    class Meta:
        model = VideoLesson

        fields = (
            "section",
            "title",
            "video_file",
            "order",
            "duration_minutes",
            "is_preview",
        )

        widgets = {
            "section": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter the lesson title",
                }
            ),
            "video_file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        "video/mp4,video/webm,"
                        "video/quicktime,video/x-m4v"
                    ),
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                }
            ),
            "duration_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "For example: 15",
                }
            ),
            "is_preview": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, course, **kwargs):
        self.course = course
        super().__init__(*args, **kwargs)

        self.fields["section"].queryset = (
            CourseSection.objects
            .filter(course=course)
            .order_by("order")
        )

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if len(title) < 3:
            raise forms.ValidationError(
                "The lesson title must contain at least 3 characters."
            )

        return title

    def clean_video_file(self):
        video_file = self.cleaned_data.get("video_file")

        if (
            video_file
            and video_file.size > self.maximum_file_size
        ):
            raise forms.ValidationError(
                "The video file must be 200 MB or smaller."
            )

        return video_file

    def clean(self):
        cleaned_data = super().clean()

        section = cleaned_data.get("section")
        order = cleaned_data.get("order")

        if section and section.course_id != self.course.pk:
            self.add_error(
                "section",
                "The selected section does not belong to this course.",
            )

        if section and order:
            duplicate_exists = VideoLesson.objects.filter(
                section=section,
                order=order,
            ).exists()

            if duplicate_exists:
                self.add_error(
                    "order",
                    "Another lesson already uses this order number.",
                )

        return cleaned_data