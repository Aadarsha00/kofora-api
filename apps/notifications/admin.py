from django.contrib import admin

from .models import NotificationLog, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "subject", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("recipient", "subject")
