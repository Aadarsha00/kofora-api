from django.utils.text import slugify
from rest_framework import serializers

from apps.products.models import Product
from apps.products.serializers import ProductSerializer
from .models import Collab, HomepageTile, SiteImage


class SiteImageSerializer(serializers.ModelSerializer):
    # DRF returns an absolute URL when the request is in the serializer context.
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)
    video = serializers.FileField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = SiteImage
        fields = ("id", "key", "image", "video", "alt_text")

    def validate(self, attrs):
        """A slot is only useful with at least one asset behind it."""
        image = attrs.get("image", getattr(self.instance, "image", None))
        video = attrs.get("video", getattr(self.instance, "video", None))
        if not image and not video:
            raise serializers.ValidationError(
                {"image": ["Upload an image or a video for this slot."]}
            )
        return attrs


class HomepageTileSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = HomepageTile
        fields = (
            "id",
            "key",
            "title",
            "href",
            "image",
            "alt_text",
            "sort_order",
            "is_active",
        )
        read_only_fields = ("key",)

    def validate_href(self, value):
        value = value.strip()
        if not value.startswith(("/", "https://", "http://")):
            raise serializers.ValidationError(
                "Use a storefront path beginning with / or a complete web URL."
            )
        return value

    def create(self, validated_data):
        base_key = slugify(validated_data["title"]) or "homepage-tile"
        key = base_key
        suffix = 2
        while HomepageTile.objects.filter(key=key).exists():
            key = f"{base_key}-{suffix}"
            suffix += 1
        validated_data["key"] = key
        return super().create(validated_data)


class CollabSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(use_url=True, required=False, allow_null=True)
    banner_image = serializers.ImageField(use_url=True, required=False, allow_null=True)
    hero_image = serializers.ImageField(use_url=True, required=False, allow_null=True)

    # Read side returns the full products so the landing page renders in one
    # request; the write side takes ids.
    products = ProductSerializer(many=True, read_only=True)
    product_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        queryset=Product.objects.all(),
        source="products",
    )
    product_count = serializers.SerializerMethodField()
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = Collab
        fields = (
            "id",
            "name",
            "slug",
            "partner_name",
            "tagline",
            "description",
            "logo",
            "banner_image",
            "hero_image",
            "accent_color",
            "text_color",
            "cta_label",
            "starts_at",
            "ends_at",
            "is_active",
            "show_on_homepage",
            "sort_order",
            "is_live",
            "products",
            "product_ids",
            "product_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("slug",)

    def get_product_count(self, obj):
        return obj.products.count()

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": ["End date must be after the start date."]})
        return attrs

    @staticmethod
    def _validate_hex(value):
        value = (value or "").strip()
        if value and not (value.startswith("#") and len(value) == 7):
            raise serializers.ValidationError("Use a 6-digit hex colour such as #253E38.")
        return value

    def validate_accent_color(self, value):
        return self._validate_hex(value)

    def validate_text_color(self, value):
        return self._validate_hex(value)

    def create(self, validated_data):
        base_slug = slugify(validated_data["name"]) or "collab"
        slug = base_slug
        suffix = 2
        while Collab.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        validated_data["slug"] = slug
        return super().create(validated_data)


class CollabSummarySerializer(CollabSerializer):
    """List/banner payload — drops the nested products to keep it light."""

    class Meta(CollabSerializer.Meta):
        fields = tuple(f for f in CollabSerializer.Meta.fields if f != "products")
