from rest_framework import serializers

from .models import InternationalShipping, ShippingMethod, ShippingRateRule, ShippingZone


class ShippingRateRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingRateRule
        fields = "__all__"


class ShippingMethodSerializer(serializers.ModelSerializer):
    rate_rules = ShippingRateRuleSerializer(many=True, read_only=True)

    class Meta:
        model = ShippingMethod
        fields = ("id", "zone", "name", "code", "base_rate", "free_shipping_threshold", "is_active", "rate_rules")


class ShippingZoneSerializer(serializers.ModelSerializer):
    methods = ShippingMethodSerializer(many=True, read_only=True)

    class Meta:
        model = ShippingZone
        fields = ("id", "name", "country_code", "state_code", "is_active", "methods")


class InternationalShippingSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True, allow_null=True)
    shipping_method_name = serializers.CharField(source="shipping_method.name", read_only=True, allow_null=True)

    class Meta:
        model = InternationalShipping
        fields = (
            "id",
            "title",
            "zone",
            "zone_name",
            "shipping_method",
            "shipping_method_name",
            "destination_country",
            "destination_country_code",
            "destination_region",
            "service_name",
            "carrier",
            "delivery_time",
            "handling_time",
            "base_rate",
            "additional_item_rate",
            "free_shipping_threshold",
            "currency",
            "duties_paid_by",
            "customs_notes",
            "return_policy",
            "restrictions",
            "notes",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        )
