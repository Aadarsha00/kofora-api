from django.contrib import admin

from .models import CouponCode, Discount, DiscountRule, DiscountUsage


class CouponCodeInline(admin.TabularInline):
    model = CouponCode
    extra = 0


class DiscountRuleInline(admin.TabularInline):
    model = DiscountRule
    extra = 0


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "discount_type", "is_active", "is_auto_applied", "is_stackable")
    list_filter = ("discount_type", "is_active", "is_auto_applied", "is_stackable")
    search_fields = ("name",)
    inlines = [CouponCodeInline, DiscountRuleInline]


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ("id", "discount", "user", "coupon_code", "order_id", "created_at")
    search_fields = ("user__email", "order_id")
