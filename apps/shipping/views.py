from rest_framework import viewsets

from .models import ShippingMethod, ShippingZone
from .serializers import ShippingMethodSerializer, ShippingZoneSerializer


class ShippingZoneViewSet(viewsets.ModelViewSet):
    queryset = ShippingZone.objects.prefetch_related("methods").all()
    serializer_class = ShippingZoneSerializer


class ShippingMethodViewSet(viewsets.ModelViewSet):
    queryset = ShippingMethod.objects.prefetch_related("rate_rules").all()
    serializer_class = ShippingMethodSerializer
