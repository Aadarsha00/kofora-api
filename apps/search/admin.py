from django.contrib import admin

from .models import SearchQueryLog


@admin.register(SearchQueryLog)
class SearchQueryLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "query", "category_slug", "size", "color", "created_at")
    search_fields = ("query", "category_slug", "size", "color", "user__email")
