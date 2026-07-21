from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdminStaff
from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    lookup_field = "slug"
    filterset_fields = ("is_active", "parent", "taxonomy_group")
    search_fields = ("name", "description", "slug")
    ordering_fields = ("sort_order", "name", "created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        availability = {}
        rows = (
            Category.objects.filter(
                is_active=True,
                products__is_active=True,
                products__is_published=True,
                products__categories__is_active=True,
                products__categories__taxonomy_group=Category.TAXONOMY_AUDIENCE,
            )
            .values_list("id", "products__categories__slug")
            .distinct()
        )

        for category_id, audience_slug in rows:
            availability.setdefault(category_id, set()).add(audience_slug)

        context["category_audience_availability"] = availability
        return context

    def get_queryset(self):
        queryset = Category.objects.select_related("parent").all()
        # Only show parent categories in the list view (children shown in nested array)
        if self.action == "list":
            queryset = queryset.filter(parent__isnull=True)
        return queryset
