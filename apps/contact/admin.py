from django.contrib import admin

from .models import ContactSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "topic", "status", "created_at")
    list_filter = ("topic", "status", "created_at")
    search_fields = ("first_name", "last_name", "email", "order_number", "message")
    readonly_fields = ("created_at", "updated_at")
