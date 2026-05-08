from rest_framework import serializers

from .models import Category


class CategoryChildSerializer(serializers.ModelSerializer):
    """Recursive serializer for nested categories"""
    parent = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "parent",
            "name",
            "slug",
            "description",
            "is_active",
            "sort_order",
            "seo_title",
            "seo_description",
            "children",
        )

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategoryChildSerializer(children, many=True).data


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "parent",
            "name",
            "slug",
            "description",
            "is_active",
            "sort_order",
            "seo_title",
            "seo_description",
            "children",
        )

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategoryChildSerializer(children, many=True).data
