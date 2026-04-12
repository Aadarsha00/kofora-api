from rest_framework import serializers

from .models import Bundle, BundleItem, Product, ProductImage, ProductVariant


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "sort_order", "is_active")


class ProductVariantSerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "sku",
            "barcode",
            "title",
            "size",
            "color",
            "price",
            "compare_at_price",
            "cost_price",
            "stock_quantity",
            "reserved_quantity",
            "available_quantity",
            "low_stock_threshold",
            "is_active",
            "image_override",
            "weight_grams",
        )


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "brand",
            "short_description",
            "full_description",
            "is_active",
            "is_featured",
            "base_currency",
            "is_published",
            "seo_title",
            "seo_description",
            "categories",
            "images",
            "variants",
            "created_at",
            "updated_at",
        )


class BundleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BundleItem
        fields = ("id", "variant", "quantity")


class BundleSerializer(serializers.ModelSerializer):
    items = BundleItemSerializer(many=True, read_only=True)

    class Meta:
        model = Bundle
        fields = ("id", "product", "name", "slug", "bundle_price", "compare_at_price", "is_active", "items")
