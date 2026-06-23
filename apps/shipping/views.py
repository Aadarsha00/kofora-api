from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdminStaff
from .models import InternationalShipping, ShippingMethod, ShippingZone
from .serializers import InternationalShippingSerializer, ShippingMethodSerializer, ShippingZoneSerializer


class ShippingZoneViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = ShippingZone.objects.prefetch_related("methods").all()
    serializer_class = ShippingZoneSerializer


class ShippingMethodViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = ShippingMethod.objects.prefetch_related("rate_rules").all()
    serializer_class = ShippingMethodSerializer


class InternationalShippingViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    serializer_class = InternationalShippingSerializer
    filterset_fields = (
        "is_active",
        "zone",
        "shipping_method",
        "destination_country_code",
        "currency",
        "duties_paid_by",
    )
    search_fields = (
        "title",
        "destination_country",
        "destination_country_code",
        "destination_region",
        "service_name",
        "carrier",
        "zone__name",
        "shipping_method__name",
        "shipping_method__code",
    )
    ordering_fields = ("sort_order", "destination_country", "base_rate", "created_at", "updated_at")

    def get_queryset(self):
        return InternationalShipping.objects.select_related("zone", "shipping_method").all()
