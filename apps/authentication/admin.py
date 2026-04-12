from django.contrib import admin

from .models import EmailOTP, GoogleOAuthAccount, PasswordResetToken


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "code", "is_used", "expires_at", "created_at")
    list_filter = ("is_used",)
    search_fields = ("email", "code")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_used", "expires_at", "created_at")
    list_filter = ("is_used",)
    search_fields = ("user__email", "token")


@admin.register(GoogleOAuthAccount)
class GoogleOAuthAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "google_sub", "email", "created_at")
    search_fields = ("user__email", "google_sub", "email")
