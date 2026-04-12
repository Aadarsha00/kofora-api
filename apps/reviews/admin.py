from django.contrib import admin

from .models import Review, ReviewImage


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "product", "rating", "is_verified_purchase", "moderation_status", "is_published", "created_at")
    list_filter = ("is_verified_purchase", "moderation_status", "is_published", "rating")
    search_fields = ("customer__email", "product__name", "title")
    inlines = [ReviewImageInline]
