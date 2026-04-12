from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
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
        return [{"id": child.id, "name": child.name, "slug": child.slug} for child in obj.children.filter(is_active=True)]
