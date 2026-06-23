from django.db import models
from django.db.models.expressions import RawSQL
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrStaff, ReadOnlyOrAdminStaff
from apps.core.responses import api_error, api_success

from .models import Bundle, Product, ProductImage, ProductVariant
from .serializers import (
    AdminProductVariantSerializer,
    BundleSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
    ProductSerializer,
    ProductVariantLookupSerializer,
)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = Product.objects.select_related("international_shipping").prefetch_related("categories", "images", "variants").all()
    filterset_fields = ("is_active", "is_featured", "is_published", "base_currency", "categories", "slug")
    search_fields = ("name", "short_description", "full_description", "brand")
    ordering_fields = ("created_at", "name", "sales_count")

    def get_queryset(self):
        sales_count_sql = """
            COALESCE((
                SELECT SUM(oi.quantity)
                FROM order_items oi
                INNER JOIN orders o ON o.id = oi.order_id
                INNER JOIN product_variants pv ON pv.sku = oi.variant_sku
                WHERE pv.product_id = products.id
                  AND o.payment_status = %s
            ), 0)
        """

        return super().get_queryset().annotate(
            sales_count=RawSQL(sales_count_sql, ("paid",), output_field=models.IntegerField())
        )


class ProductVariantViewSet(viewsets.ModelViewSet):
    serializer_class = AdminProductVariantSerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = ProductVariant.objects.select_related("product").all()
    filterset_fields = ("product", "is_active", "size", "color")
    search_fields = ("sku", "title", "size", "color", "product__name", "product__slug")
    ordering_fields = ("price", "created_at", "stock_quantity", "low_stock_threshold", "sku")

    def get_queryset(self):
        queryset = super().get_queryset()
        stock_status = self.request.query_params.get("stock_status", "").strip().lower()
        if stock_status == "out":
            return queryset.filter(stock_quantity__lte=models.F("reserved_quantity"))
        if stock_status == "low":
            return queryset.filter(
                stock_quantity__gt=models.F("reserved_quantity"),
                stock_quantity__lte=models.F("low_stock_threshold"),
            )
        if stock_status == "available":
            return queryset.filter(stock_quantity__gt=models.F("reserved_quantity"))
        return queryset


class BundleViewSet(viewsets.ModelViewSet):
    serializer_class = BundleSerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = Bundle.objects.prefetch_related("items").all()
    filterset_fields = ("is_active", "product")


class ProductVariantLookupView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raw_ids = request.query_params.get("ids", "")
        if not raw_ids.strip():
            return api_error("Variant ids are required", {"ids": ["Provide one or more comma-separated ids."]})

        try:
            requested_ids = [
                int(value)
                for value in raw_ids.split(",")
                if value.strip()
            ]
        except ValueError:
            return api_error("Variant ids must be integers", {"ids": ["Use comma-separated numeric ids."]})

        if not requested_ids:
            return api_error("Variant ids are required", {"ids": ["Provide one or more comma-separated ids."]})

        variants = ProductVariant.objects.select_related("product").prefetch_related(
            "images",
            "product__images",
        ).filter(
            id__in=requested_ids,
            is_active=True,
            product__is_active=True,
            product__is_published=True,
        )
        variant_by_id = {variant.id: variant for variant in variants}
        ordered_variants = [variant_by_id[variant_id] for variant_id in requested_ids if variant_id in variant_by_id]

        return api_success(
            "Product variants retrieved successfully",
            ProductVariantLookupSerializer(ordered_variants, many=True).data,
        )


class ProductImageUploadView(APIView):
    permission_classes = [IsAdminOrStaff]

    def post(self, request):
        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_obj = serializer.save()
        return api_success(
            "Product image uploaded successfully",
            ProductImageUploadSerializer(image_obj).data,
        )


class ProductImageDetailView(APIView):
    permission_classes = [IsAdminOrStaff]

    def patch(self, request, pk):
        image = ProductImage.objects.filter(pk=pk).first()
        if not image:
            return api_error("Image not found", status_code=404)
        serializer = ProductImageSerializer(image, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_success("Product image updated", ProductImageSerializer(image).data)

    def delete(self, request, pk):
        image = ProductImage.objects.filter(pk=pk).first()
        if not image:
            return api_error("Image not found", status_code=404)
        image.delete()
        return api_success("Product image deleted")
