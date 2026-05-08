import os
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ("id", "image", "alt_text")


class ReviewImageUploadSerializer(serializers.ModelSerializer):
    image_url = serializers.URLField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ReviewImage
        fields = ("id", "review", "image", "image_url", "alt_text")

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
            filename = os.path.basename(parsed.path) or "review-image.jpg"
            validated_data["image"] = ContentFile(response.content, name=filename)
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = ("id", "customer", "product", "rating", "title", "body", "is_verified_purchase", "moderation_status", "is_published", "images", "created_at")
        read_only_fields = ("customer", "is_verified_purchase", "moderation_status", "is_published")
