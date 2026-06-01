from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from decimal import Decimal, InvalidOperation

from apps.core.permissions import ReadOnlyOrAdminStaff
from apps.core.responses import api_error, api_success

from .models import CouponCode, Discount
from .serializers import CouponCodeSerializer, DiscountSerializer
from .services.discount_service import (
    apply_coupon_to_amount,
    validate_coupon_for_user,
    apply_first_order_discount,
    apply_first_order_claim_to_cart,
)
from apps.cart.models import Cart
from apps.cart.serializers import CartSerializer


class DiscountViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = Discount.objects.all().order_by("-created_at")
    serializer_class = DiscountSerializer
    filterset_fields = ("is_active", "discount_type", "is_auto_applied")
    search_fields = ("name",)
    ordering_fields = ("created_at", "name")


class CouponCodeViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    serializer_class = CouponCodeSerializer
    filterset_fields = ("is_active", "discount")

    def get_queryset(self):
        return (
            CouponCode.objects.select_related("discount")
            .exclude(discount__first_order_only=True)
            .order_by("-created_at")
        )


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
        if coupon.discount.first_order_only:
            return api_error("First-order discounts must be claimed with the email attached to your account")

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


class FirstOrderDiscountView(APIView):
    """
    Check eligibility for and return first-order discount code.
    Endpoint: POST /discounts/first-order/
    Payload: {"email": "user@example.com"}
    
    Note: This endpoint only checks if the email has already completed an order with this discount.
    The discount is not marked as "used" until the order is successfully placed.
    This allows users to get a code, and if they don't complete purchase, they can try again.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        
        if not email:
            return api_error("Email is required", {"email": ["This field is required."]})
        
        # Basic email validation
        if "@" not in email or "." not in email:
            return api_error("Invalid email format")
        
        success, message, claim = apply_first_order_discount(email)
        
        if not success:
            return api_error(message)
        
        # Return claim details only. The reusable coupon code stays server-side.
        return api_success(
            "First-order discount available",
            {
                "claim_token": str(claim.token),
                "discount_id": claim.discount.id,
                "discount_type": claim.discount.discount_type,
                "discount_amount": claim.discount.flat_amount or claim.discount.percentage,
                "expires_at": claim.expires_at,
                "message": "First-order discount saved for checkout"
            }
        )


class FirstOrderDiscountApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("claim_token", "").strip()
        if not token:
            return api_error("Discount claim token is required", {"claim_token": ["This field is required."]})

        cart, _ = Cart.objects.get_or_create(user=request.user)
        success, message, cart = apply_first_order_claim_to_cart(token, request.user, cart)
        if not success:
            return api_error(message)

        return api_success(message, CartSerializer(cart).data)
