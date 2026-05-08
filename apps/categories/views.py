from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "slug"
    filterset_fields = ("is_active", "parent")
    search_fields = ("name", "description")
    ordering_fields = ("sort_order", "name", "created_at")

    def get_queryset(self):
        queryset = Category.objects.select_related("parent").all()
        # Only show parent categories in the list view (children shown in nested array)
        if self.action == "list":
            queryset = queryset.filter(parent__isnull=True)
        return queryset
