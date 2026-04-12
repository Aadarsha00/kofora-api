from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from decimal import Decimal, InvalidOperation

from apps.core.responses import api_error, api_success

from .models import CouponCode, Discount
from .serializers import CouponCodeSerializer, DiscountSerializer
from .services.discount_service import apply_coupon_to_amount, validate_coupon_for_user


class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    filterset_fields = ("is_active", "discount_type", "is_auto_applied")


class CouponCodeViewSet(viewsets.ModelViewSet):
    queryset = CouponCode.objects.select_related("discount").all()
    serializer_class = CouponCodeSerializer
    filterset_fields = ("is_active",)


class CouponValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").strip()
        subtotal = request.data.get("subtotal")
        if not code:
            return api_error("Coupon code is required", {"code": ["This field is required."]})
        if subtotal is None:
            return api_error("Subtotal is required", {"subtotal": ["This field is required."]})
        try:
            subtotal = Decimal(str(subtotal))
        except (InvalidOperation, TypeError):
            return api_error("Invalid subtotal", {"subtotal": ["Enter a valid decimal amount."]})

        coupon = CouponCode.objects.select_related("discount").filter(code=code).first()
        if not coupon:
            return api_error("Coupon not found")

        is_valid, reason = validate_coupon_for_user(coupon, request.user, subtotal)
        if not is_valid:
            return api_error(reason)

        discount_amount = apply_coupon_to_amount(coupon, subtotal)
        return api_success(
            "Coupon validated successfully",
            {
                "code": coupon.code,
                "discount_amount": discount_amount,
                "message": reason,
            },
        )
