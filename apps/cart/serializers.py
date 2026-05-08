from rest_framework import serializers

from .models import Cart, CartBundleItem, CartVariantItem
from .services.cart_service import calculate_cart_totals
from apps.products.models import ProductVariant


class ProductVariantDetailSerializer(serializers.ModelSerializer):
    """Lightweight serializer for variants in cart responses"""
    product_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.SlugField(source="product.slug", read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product_id",
            "product_name",
            "product_slug",
            "sku",
            "title",
            "size",
            "color",
            "price",
            "stock_quantity",
            "available_quantity",
            "image_override",
        )


class CartVariantItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantDetailSerializer(read_only=True)

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
    applied_coupon = serializers.SerializerMethodField()
    applied_discount_claim = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "currency",
            "shipping_address",
            "billing_address",
            "shipping_method",
            "applied_coupon",
            "applied_discount_claim",
            "variant_items",
            "bundle_items",
            "totals",
            "is_abandoned",
            "abandoned_at",
        )

    def get_applied_coupon(self, obj):
        """Return the coupon code instead of just the ID"""
        if obj.applied_coupon:
            return obj.applied_coupon.code
        return None

    def get_applied_discount_claim(self, obj):
        if obj.applied_discount_claim:
            return {
                "claim_token": str(obj.applied_discount_claim.token),
                "email": obj.applied_discount_claim.email,
                "status": obj.applied_discount_claim.status,
                "expires_at": obj.applied_discount_claim.expires_at,
            }
        return None

    def get_totals(self, obj):
        return calculate_cart_totals(obj)
