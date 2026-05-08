from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from apps.core.responses import api_success

from .models import Bundle, Product, ProductImage
from .serializers import BundleSerializer, ProductImageUploadSerializer, ProductSerializer


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


class ProductImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_obj = serializer.save()
        return api_success(
            "Product image uploaded successfully",
            ProductImageUploadSerializer(image_obj).data,
        )
