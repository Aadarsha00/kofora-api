from rest_framework import serializers

from .models import Attribute, AttributeOption, ProductAttributeValue, VariantAttributeValue


class AttributeOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeOption
        fields = ("id", "attribute", "value", "sort_order", "is_active")


class AttributeSerializer(serializers.ModelSerializer):
    options = AttributeOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Attribute
        fields = ("id", "code", "name", "is_active", "options")
