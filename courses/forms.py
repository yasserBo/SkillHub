from decimal import Decimal

from django import forms

from .models import Course


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