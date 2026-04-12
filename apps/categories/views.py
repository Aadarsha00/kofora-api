from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Category.objects.select_related("parent").all()
    filterset_fields = ("is_active", "parent")
    search_fields = ("name", "description")
    ordering_fields = ("sort_order", "name", "created_at")
