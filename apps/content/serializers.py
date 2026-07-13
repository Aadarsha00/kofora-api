from rest_framework import serializers

from .models import SiteImage


class SiteImageSerializer(serializers.ModelSerializer):
    # DRF returns an absolute URL when the request is in the serializer context.
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = SiteImage
        fields = ("id", "key", "image", "alt_text")
