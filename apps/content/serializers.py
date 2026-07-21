from django.utils.text import slugify
from rest_framework import serializers

from .models import HomepageTile, SiteImage


class SiteImageSerializer(serializers.ModelSerializer):
    # DRF returns an absolute URL when the request is in the serializer context.
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = SiteImage
        fields = ("id", "key", "image", "alt_text")


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
