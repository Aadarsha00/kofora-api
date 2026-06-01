import os
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Bundle, BundleItem, Product, ProductImage, ProductVariant


class ProductImageSerializer(serializers.ModelSerializer):
    variant_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "sort_order", "is_active", "variant", "variant_id")


class ProductImageUploadSerializer(serializers.ModelSerializer):
    image_url = serializers.URLField(required=False, allow_blank=True, write_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        source="variant",
        queryset=ProductVariant.objects.select_related("product").all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ProductImage
        fields = ("id", "product", "image", "image_url", "alt_text", "sort_order", "is_active", "variant_id")

    def validate(self, attrs):
        image_file = attrs.get("image")
        image_url = attrs.get("image_url")
        if not image_file and not image_url:
            raise serializers.ValidationError({"image": ["Either image upload or image_url is required."]})

        product = attrs.get("product")
        variant = attrs.get("variant")
        if product and variant and variant.product_id != product.id:
            raise serializers.ValidationError(
                {"variant_id": ["Selected variant must belong to the selected product."]}
            )
        return attrs

    def create(self, validated_data):
        image_url = validated_data.pop("image_url", "")
        image_file = validated_data.get("image")
        if not image_file and image_url:
            try:
                response = requests.get(image_url, timeout=15)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise serializers.ValidationError({"image_url": ["Could not fetch image_url."]}) from exc
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


class AdminProductVariantSerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product",
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


class ProductVariantLookupSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.SlugField(source="product.slug", read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    image = serializers.SerializerMethodField()
    image_alt_text = serializers.SerializerMethodField()

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
            "compare_at_price",
            "available_quantity",
            "image_override",
            "image",
            "image_alt_text",
        )

    def _selected_image(self, obj):
        variant_image = obj.images.filter(is_active=True).order_by("sort_order", "id").first()
        if variant_image:
            return variant_image
        return obj.product.images.filter(is_active=True, variant__isnull=True).order_by("sort_order", "id").first()

    def get_image(self, obj):
        if obj.image_override:
            return obj.image_override.url
        image = self._selected_image(obj)
        return image.image.url if image else None

    def get_image_alt_text(self, obj):
        image = self._selected_image(obj)
        if image and image.alt_text:
            return image.alt_text
        return obj.title or obj.product.name


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
