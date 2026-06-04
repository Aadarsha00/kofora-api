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
            "taxonomy_group",
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
            "taxonomy_group",
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

    def validate(self, attrs):
        taxonomy_group = attrs.get("taxonomy_group", getattr(self.instance, "taxonomy_group", ""))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))

        if taxonomy_group in {Category.TAXONOMY_PRODUCT_FAMILY, Category.TAXONOMY_AUDIENCE} and parent is not None:
            raise serializers.ValidationError({"parent": ["Product family and audience categories must be top level."]})

        if taxonomy_group in {Category.TAXONOMY_HEIGHT, Category.TAXONOMY_PURPOSE}:
            if parent is None or parent.slug != "socks":
                raise serializers.ValidationError({"parent": ["Height and purpose categories must be children of Socks."]})

        return attrs
