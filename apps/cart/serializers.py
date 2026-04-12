from rest_framework import serializers

from .models import Cart, CartBundleItem, CartVariantItem
from .services.cart_service import calculate_cart_totals


class CartVariantItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartVariantItem
        fields = ("id", "variant", "quantity")


class CartBundleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartBundleItem
        fields = ("id", "bundle", "quantity")


class CartSerializer(serializers.ModelSerializer):
    variant_items = CartVariantItemSerializer(many=True, read_only=True)
    bundle_items = CartBundleItemSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "currency",
            "shipping_address",
            "billing_address",
            "shipping_method",
            "applied_coupon",
            "variant_items",
            "bundle_items",
            "totals",
            "is_abandoned",
            "abandoned_at",
        )

    def get_totals(self, obj):
        return calculate_cart_totals(obj)
