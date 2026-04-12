from django.contrib import admin

from .models import Cart, CartBundleItem, CartVariantItem


class CartVariantItemInline(admin.TabularInline):
    model = CartVariantItem
    extra = 0


class CartBundleItemInline(admin.TabularInline):
    model = CartBundleItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "currency", "applied_coupon", "is_abandoned", "updated_at")
    list_filter = ("currency", "is_abandoned")
    search_fields = ("user__email",)
    inlines = [CartVariantItemInline, CartBundleItemInline]
