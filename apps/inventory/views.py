from rest_framework import viewsets

from .models import InventoryAdjustment
from .serializers import InventoryAdjustmentSerializer


class InventoryAdjustmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryAdjustment.objects.select_related("variant", "adjusted_by")
    serializer_class = InventoryAdjustmentSerializer
    filterset_fields = ("reason", "variant")
