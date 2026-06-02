from django.db import transaction
from rest_framework import viewsets

from apps.core.permissions import IsAdminOrStaff

from .models import InventoryAdjustment
from .serializers import InventoryAdjustmentSerializer


class InventoryAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = InventoryAdjustment.objects.select_related("variant", "adjusted_by")
    serializer_class = InventoryAdjustmentSerializer
    permission_classes = [IsAdminOrStaff]
    filterset_fields = ("reason", "variant")
    search_fields = ("variant__sku", "variant__product__name", "reference", "notes")
    ordering_fields = ("created_at", "quantity_delta")

    def perform_create(self, serializer):
        with transaction.atomic():
            adjustment = serializer.save(adjusted_by=self.request.user)
            variant = adjustment.variant
            variant.stock_quantity += adjustment.quantity_delta
            variant.save(update_fields=["stock_quantity", "updated_at"])
