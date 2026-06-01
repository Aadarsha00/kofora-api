from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdminStaff
from .models import ShippingMethod, ShippingZone
from .serializers import ShippingMethodSerializer, ShippingZoneSerializer


class ShippingZoneViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = ShippingZone.objects.prefetch_related("methods").all()
    serializer_class = ShippingZoneSerializer


class ShippingMethodViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = ShippingMethod.objects.prefetch_related("rate_rules").all()
    serializer_class = ShippingMethodSerializer
