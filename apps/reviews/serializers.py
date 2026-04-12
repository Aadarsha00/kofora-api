from rest_framework import serializers

from .models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ("id", "image", "alt_text")


class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = ("id", "customer", "product", "rating", "title", "body", "is_verified_purchase", "moderation_status", "is_published", "images", "created_at")
        read_only_fields = ("customer", "is_verified_purchase", "moderation_status", "is_published")
