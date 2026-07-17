from django.contrib import admin

from .models import Category, Course


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
    )

    search_fields = (
        "name",
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "instructor",
        "category",
        "level",
        "price",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "level",
        "category",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "instructor__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )