import os
import re
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from rest_framework import serializers

from apps.categories.models import Category

from .models import Bundle, BundleItem, Product, ProductImage, ProductVariant

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
PRODUCT_FAMILY_CATEGORY_SLUGS = {"socks"}
AUDIENCE_CATEGORY_SLUGS = {"men", "women", "kids", "unisex"}
SOCK_HEIGHT_CATEGORY_SLUGS = {
    "no-show",
    "ankle",
    "ankel",
    "quarter",
    "crew",
    "crew-socks",
    "half-calf",
    "calf",
    "knee-high",
}


def normalize_color_mix(value):
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError("Color mix must be a list.")

    normalized = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise serializers.ValidationError(f"Color mix item {index + 1} must be an object.")

        name = str(item.get("name", "")).strip()
        hex_value = str(item.get("hex", "")).strip()
        quantity_value = item.get("quantity", 1)

        if not name:
            raise serializers.ValidationError(f"Color mix item {index + 1} needs a color name.")
        if hex_value and not HEX_COLOR_RE.match(hex_value):
            raise serializers.ValidationError(f"Color mix item {index + 1} has an invalid hex color.")

        try:
            quantity = int(quantity_value)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(f"Color mix item {index + 1} needs a valid quantity.") from exc

        if quantity < 1:
            raise serializers.ValidationError(f"Color mix item {index + 1} quantity must be at least 1.")

        normalized.append(
            {
                "name": name[:60],
                "hex": hex_value,
                "quantity": quantity,
            }
        )

    return normalized


class ProductImageSerializer(serializers.ModelSerializer):
    variant_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "sort_order", "is_primary", "is_active", "variant", "variant_id")


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
        fields = ("id", "product", "image", "image_url", "alt_text", "sort_order", "is_primary", "is_active", "variant_id")

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

    def validate_color_mix(self, value):
        return normalize_color_mix(value)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "sku",
            "barcode",
            "title",
            "size",
            "color",
            "color_mix",
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
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.SlugField(source="product.slug", read_only=True)

    def validate_color_mix(self, value):
        return normalize_color_mix(value)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product",
            "product_name",
            "product_slug",
            "sku",
            "barcode",
            "title",
            "size",
            "color",
            "color_mix",
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
            "color_mix",
            "price",
            "compare_at_price",
            "available_quantity",
            "image_override",
            "image",
            "image_alt_text",
        )

    def _variant_image(self, obj):
        color_variant_ids = obj.product.variants.filter(color=obj.color).values_list("id", flat=True)
        return obj.product.images.filter(
            is_active=True,
            variant_id__in=color_variant_ids,
        ).order_by("-is_primary", "sort_order", "id").first()

    def _product_image(self, obj):
        return obj.product.images.filter(is_active=True, variant__isnull=True).order_by("-is_primary", "sort_order", "id").first()

    def get_image(self, obj):
        image = self._variant_image(obj)
        if image:
            return image.image.url
        if obj.image_override:
            return obj.image_override.url
        image = self._product_image(obj)
        return image.image.url if image else None

    def get_image_alt_text(self, obj):
        image = self._variant_image(obj) or self._product_image(obj)
        if image and image.alt_text:
            return image.alt_text
        return obj.title or obj.product.name


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    sales_count = serializers.IntegerField(read_only=True, default=0)

    def validate(self, attrs):
        categories = attrs.get("categories")

        if categories is None:
            if self.instance is not None:
                return attrs
            categories = []

        category_slugs = {category.slug for category in categories}
        category_groups = {category.taxonomy_group for category in categories if category.taxonomy_group}
        has_product_family = (
            Category.TAXONOMY_PRODUCT_FAMILY in category_groups
            or bool(category_slugs & PRODUCT_FAMILY_CATEGORY_SLUGS)
        )
        has_audience = (
            Category.TAXONOMY_AUDIENCE in category_groups
            or bool(category_slugs & AUDIENCE_CATEGORY_SLUGS)
        )
        has_height = (
            Category.TAXONOMY_HEIGHT in category_groups
            or bool(category_slugs & SOCK_HEIGHT_CATEGORY_SLUGS)
        )

        if not has_product_family:
            raise serializers.ValidationError({"categories": ["Choose a product family."]})
        if not has_audience:
            raise serializers.ValidationError({"categories": ["Choose at least one audience."]})
        if "socks" in category_slugs and not has_height:
            raise serializers.ValidationError({"categories": ["Choose a sock height."]})

        return attrs

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
            "sales_count",
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
