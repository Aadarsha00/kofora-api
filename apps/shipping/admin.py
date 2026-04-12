from django.contrib import admin

from .models import ShippingMethod, ShippingRateRule, ShippingZone


class ShippingRateRuleInline(admin.TabularInline):
    model = ShippingRateRule
    extra = 0


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country_code", "state_code", "is_active")
    list_filter = ("country_code", "is_active")
    search_fields = ("name",)


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "zone", "base_rate", "is_active")
    list_filter = ("is_active", "zone")
    search_fields = ("name", "code")
    inlines = [ShippingRateRuleInline]
