from django.contrib import admin

from .models import SiteImage


@admin.register(SiteImage)
class SiteImageAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "image", "alt_text", "updated_at")
    search_fields = ("key", "alt_text")
    ordering = ("key",)
