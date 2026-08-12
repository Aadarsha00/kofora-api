from decimal import Decimal

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
        fields = ("id", "zone", "name", "code", "base_rate", "ups_service_code", "free_shipping_threshold", "is_active", "rate_rules")


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


class UPSAddressSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line_1 = serializers.CharField(max_length=255)
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120)
    state_province = serializers.CharField(max_length=120, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=2)


class UPSPackageSerializer(serializers.Serializer):
    weight = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=Decimal("0.1"))
    length = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    width = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    height = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)


class UPSRateRequestSerializer(serializers.Serializer):
    REQUEST_OPTIONS = ("Shop", "Rate")

    destination = UPSAddressSerializer()
    packages = UPSPackageSerializer(many=True)
    request_option = serializers.ChoiceField(choices=REQUEST_OPTIONS, default="Shop")
    service_code = serializers.CharField(max_length=3, required=False, allow_blank=True)

    def validate_packages(self, value):
        if not value:
            raise serializers.ValidationError("At least one package is required.")
        return value

    def validate(self, attrs):
        if attrs.get("request_option") == "Rate" and not attrs.get("service_code"):
            raise serializers.ValidationError(
                {"service_code": "Required when request_option is 'Rate'."}
            )
        return attrs
