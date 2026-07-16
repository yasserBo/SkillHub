from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import InstructorProfile, LearnerProfile, User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "account_status",
        "is_staff",
        "date_joined",
    )

    list_filter = (
        "role",
        "account_status",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("email",)

    fieldsets = (
        (
            "Login information",
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "role",
                    "account_status",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            "Create a SkillHub user",
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "account_status",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    readonly_fields = (
        "last_login",
        "date_joined",
    )
    actions = (
        "activate_accounts",
        "suspend_accounts",
        "deactivate_accounts",
    )

    list_per_page = 25

    def _change_account_status(
        self,
        request,
        queryset,
        new_status,
    ):
        """Change account status while protecting administrators."""

        updated_count = 0
        skipped_count = 0

        for user in queryset:
            # Do not allow administrators to block themselves
            # or other superusers through bulk actions.
            if user.pk == request.user.pk or user.is_superuser:
                skipped_count += 1
                continue

            user.account_status = new_status
            user.save(
                update_fields=[
                    "account_status",
                    "is_active",
                ]
            )

            updated_count += 1

        if updated_count:
            self.message_user(
                request,
                f"{updated_count} account(s) updated successfully.",
                level=messages.SUCCESS,
            )

        if skipped_count:
            self.message_user(
                request,
                (
                    f"{skipped_count} administrator account(s) "
                    "were protected and not changed."
                ),
                level=messages.WARNING,
            )


    @admin.action(description="Activate selected accounts")
    def activate_accounts(self, request, queryset):
        self._change_account_status(
            request,
            queryset,
            User.AccountStatus.ACTIVE,
        )


    @admin.action(description="Suspend selected accounts")
    def suspend_accounts(self, request, queryset):
        self._change_account_status(
            request,
            queryset,
            User.AccountStatus.SUSPENDED,
        )


    @admin.action(description="Deactivate selected accounts")
    def deactivate_accounts(self, request, queryset):
        self._change_account_status(
            request,
            queryset,
            User.AccountStatus.DEACTIVATED,
        )

@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "professional_title",
        "expertise",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "professional_title",
        "expertise",
    )

    list_filter = (
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "location",
        "updated_at",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "skills",
        "location",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.site_header = "SkillHub Administration"
admin.site.site_title = "SkillHub Admin"
admin.site.index_title = "Platform Management"