from rest_framework import serializers

from .models import ShippingMethod, ShippingRateRule, ShippingZone


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
