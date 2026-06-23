from django.contrib import admin

from .models import InternationalShipping, ShippingMethod, ShippingRateRule, ShippingZone


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


@admin.register(InternationalShipping)
class InternationalShippingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "destination_country",
        "service_name",
        "shipping_method",
        "base_rate",
        "currency",
        "is_active",
        "sort_order",
    )
    list_filter = ("is_active", "currency", "duties_paid_by", "destination_country_code", "zone", "shipping_method")
    list_editable = ("is_active", "sort_order")
    list_select_related = ("zone", "shipping_method")
    search_fields = (
        "title",
        "destination_country",
        "destination_country_code",
        "destination_region",
        "service_name",
        "carrier",
        "zone__name",
        "shipping_method__name",
        "shipping_method__code",
    )
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Destination",
            {
                "fields": (
                    "title",
                    "zone",
                    "destination_country",
                    "destination_country_code",
                    "destination_region",
                    "is_active",
                    "sort_order",
                )
            },
        ),
        (
            "Service",
            {
                "fields": (
                    "shipping_method",
                    "service_name",
                    "carrier",
                    "delivery_time",
                    "handling_time",
                )
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "currency",
                    "base_rate",
                    "additional_item_rate",
                    "free_shipping_threshold",
                    "duties_paid_by",
                )
            },
        ),
        (
            "Policies",
            {
                "fields": (
                    "customs_notes",
                    "return_policy",
                    "restrictions",
                    "notes",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
