from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "taxonomy_group", "parent", "is_active", "sort_order")
    list_filter = ("taxonomy_group", "is_active", "parent")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")
    fields = (
        "parent",
        "name",
        "slug",
        "taxonomy_group",
        "image",
        "description",
        "is_active",
        "sort_order",
        "seo_title",
        "seo_description",
    )
