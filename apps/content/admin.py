from django.contrib import admin

from .models import HomepageTile, SiteImage


@admin.register(SiteImage)
class SiteImageAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "image", "alt_text", "updated_at")
    search_fields = ("key", "alt_text")
    ordering = ("key",)


@admin.register(HomepageTile)
class HomepageTileAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "href", "sort_order", "is_active", "updated_at")
    list_editable = ("sort_order", "is_active")
    search_fields = ("title", "href", "alt_text")
    ordering = ("sort_order", "id")
