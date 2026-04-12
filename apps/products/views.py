from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Bundle, Product
from .serializers import BundleSerializer, ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Product.objects.prefetch_related("categories", "images", "variants").all()
    filterset_fields = ("is_active", "is_featured", "is_published", "base_currency", "categories")
    search_fields = ("name", "short_description", "full_description", "brand")
    ordering_fields = ("created_at", "name")


class BundleViewSet(viewsets.ModelViewSet):
    serializer_class = BundleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Bundle.objects.prefetch_related("items").all()
    filterset_fields = ("is_active", "product")
