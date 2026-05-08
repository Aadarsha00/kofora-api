import os
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Bundle, BundleItem, Product, ProductImage, ProductVariant


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "sort_order", "is_active", "variant", "variant_id")


class ProductImageUploadSerializer(serializers.ModelSerializer):
    image_url = serializers.URLField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "product", "image", "image_url", "alt_text", "sort_order", "is_active")

    def validate(self, attrs):
        image_file = attrs.get("image")
        image_url = attrs.get("image_url")
        if not image_file and not image_url:
            raise serializers.ValidationError({"image": ["Either image upload or image_url is required."]})
        return attrs

    def create(self, validated_data):
        image_url = validated_data.pop("image_url", "")
        image_file = validated_data.get("image")
        if not image_file and image_url:
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()
            parsed = urlparse(image_url)
            filename = os.path.basename(parsed.path) or "product-image.jpg"
            validated_data["image"] = ContentFile(response.content, name=filename)
        return super().create(validated_data)


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
