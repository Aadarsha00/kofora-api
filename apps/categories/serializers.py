from rest_framework import serializers

from .models import Category


def _absolute_image_url(serializer, obj):
    if not obj.image:
        return None
    url = obj.image.url
    request = serializer.context.get("request")
    return request.build_absolute_uri(url) if request else url


class CategoryChildSerializer(serializers.ModelSerializer):
    """Recursive serializer for nested categories"""
    parent = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    children = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

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
            "image",
            "children",
        )

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategoryChildSerializer(children, many=True, context=self.context).data

    def get_image(self, obj):
        return _absolute_image_url(self, obj)


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    children = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False, allow_null=True, use_url=True)

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
            "image",
            "children",
        )

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategoryChildSerializer(children, many=True, context=self.context).data

    def validate(self, attrs):
        taxonomy_group = attrs.get("taxonomy_group", getattr(self.instance, "taxonomy_group", ""))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))

        if taxonomy_group in {Category.TAXONOMY_PRODUCT_FAMILY, Category.TAXONOMY_AUDIENCE} and parent is not None:
            raise serializers.ValidationError({"parent": ["Product family and audience categories must be top level."]})

        if taxonomy_group in {Category.TAXONOMY_HEIGHT, Category.TAXONOMY_PURPOSE}:
            if parent is None or parent.slug != "socks":
                raise serializers.ValidationError({"parent": ["Height and purpose categories must be children of Socks."]})

        return attrs
