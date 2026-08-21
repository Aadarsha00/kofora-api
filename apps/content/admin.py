from django.contrib import admin

from .models import Collab, HomepageTile, SiteImage


@admin.register(SiteImage)
class SiteImageAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "image", "video", "alt_text", "updated_at")
    search_fields = ("key", "alt_text")
    ordering = ("key",)


@admin.register(HomepageTile)
class HomepageTileAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "href", "sort_order", "is_active", "updated_at")
    list_editable = ("sort_order", "is_active")
    search_fields = ("title", "href", "alt_text")
    ordering = ("sort_order", "id")


@admin.register(Collab)
class CollabAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "show_on_homepage", "starts_at", "ends_at", "sort_order")
    list_editable = ("sort_order", "is_active", "show_on_homepage")
    search_fields = ("name", "slug", "partner_name", "tagline")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("products",)
    ordering = ("sort_order", "id")
