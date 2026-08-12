from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import ReadOnlyOrAdminStaff
from apps.core.responses import api_error, api_success
from .models import InternationalShipping, ShippingMethod, ShippingZone
from .serializers import (
    InternationalShippingSerializer,
    ShippingMethodSerializer,
    ShippingZoneSerializer,
    UPSAddressSerializer,
    UPSRateRequestSerializer,
)
from .services.ups_client import UPSError, UPSNotConfigured, is_sandbox
from .services.ups_service import get_rates, track_shipment, validate_address


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


def _ups_failure(exc):
    """UPS misconfiguration is ours to fix (500); anything else is upstream (502)."""
    if isinstance(exc, UPSNotConfigured):
        return api_error(
            "UPS is not configured",
            errors={"detail": str(exc)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return api_error(
        "UPS request failed",
        errors={"detail": str(exc)},
        status_code=status.HTTP_502_BAD_GATEWAY,
    )


class UPSRateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UPSRateRequestSerializer

    def post(self, request):
        serializer = UPSRateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            rates = get_rates(
                destination=data["destination"],
                packages=data["packages"],
                request_option=data["request_option"],
                service_code=data.get("service_code") or None,
            )
        except UPSError as exc:
            return _ups_failure(exc)

        return api_success(
            "UPS rates retrieved",
            data={"sandbox": is_sandbox(), "rates": rates},
        )


class UPSTrackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tracking_number):
        try:
            tracking = track_shipment(tracking_number)
        except UPSError as exc:
            return _ups_failure(exc)

        return api_success("UPS tracking retrieved", data=tracking)


class UPSAddressValidationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UPSAddressSerializer

    def post(self, request):
        serializer = UPSAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = validate_address(serializer.validated_data)
        except UPSError as exc:
            return _ups_failure(exc)

        return api_success("UPS address validation complete", data=result)
