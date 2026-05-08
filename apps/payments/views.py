from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_error, api_success
from apps.orders.models import Order

from .models import PaymentTransaction
from .serializers import (
    PayPalCaptureRequestSerializer,
    PayPalOrderRequestSerializer,
    PaymentTransactionSerializer,
    RefundRequestSerializer,
    StripeCheckoutConfirmRequestSerializer,
    StripeCheckoutRequestSerializer,
    StripeIntentRequestSerializer,
)
from .services.provider_service import (
    PaymentProviderError,
    capture_paypal_order,
    create_paypal_order,
    create_refund,
    confirm_stripe_checkout_session,
    create_stripe_checkout_session,
    create_stripe_payment_intent,
    reconcile_paypal_event,
    reconcile_stripe_event,
    record_webhook,
    verify_paypal_signature,
    verify_stripe_signature,
)


class PaymentTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        txns = PaymentTransaction.objects.filter(order__customer=request.user)
        return api_success("Payments fetched successfully", PaymentTransactionSerializer(txns, many=True).data)


class StripeCreateIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StripeIntentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = Order.objects.filter(id=serializer.validated_data["order_id"], customer=request.user).first()
        if not order:
            return api_error("Order not found")
        try:
            txn = create_stripe_payment_intent(
                order=order,
                idempotency_key=serializer.validated_data["idempotency_key"],
            )
        except PaymentProviderError as exc:
            return api_error(str(exc))
        return api_success("Stripe payment intent created", PaymentTransactionSerializer(txn).data)


class StripeCreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StripeCheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = Order.objects.filter(id=serializer.validated_data["order_id"], customer=request.user).first()
        if not order:
            return api_error("Order not found")
        try:
            txn = create_stripe_checkout_session(
                order=order,
                idempotency_key=serializer.validated_data["idempotency_key"],
                success_url=serializer.validated_data["success_url"],
                cancel_url=serializer.validated_data["cancel_url"],
            )
        except PaymentProviderError as exc:
            return api_error(str(exc))
        return api_success("Stripe checkout session created", PaymentTransactionSerializer(txn).data)


class StripeConfirmCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StripeCheckoutConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = Order.objects.filter(id=serializer.validated_data["order_id"], customer=request.user).first()
        if not order:
            return api_error("Order not found")
        try:
            txn = confirm_stripe_checkout_session(
                order=order,
                provider_payment_id=serializer.validated_data["provider_payment_id"],
            )
        except PaymentProviderError as exc:
            return api_error(str(exc))
        return api_success("Stripe checkout session confirmed", PaymentTransactionSerializer(txn).data)


class PayPalCreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PayPalOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = Order.objects.filter(id=serializer.validated_data["order_id"], customer=request.user).first()
        if not order:
            return api_error("Order not found")
        try:
            txn = create_paypal_order(
                order=order,
                idempotency_key=serializer.validated_data["idempotency_key"],
                return_url=serializer.validated_data["return_url"],
                cancel_url=serializer.validated_data["cancel_url"],
            )
        except PaymentProviderError as exc:
            return api_error(str(exc))
        return api_success("PayPal order created", PaymentTransactionSerializer(txn).data)


class PayPalCaptureOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PayPalCaptureRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = Order.objects.filter(id=serializer.validated_data["order_id"], customer=request.user).first()
        if not order:
            return api_error("Order not found")
        try:
            txn = capture_paypal_order(
                order,
                serializer.validated_data["provider_payment_id"],
                serializer.validated_data["payer_id"],
            )
        except PaymentProviderError as exc:
            return api_error(str(exc))
        return api_success("PayPal order captured", PaymentTransactionSerializer(txn).data)


class RefundCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        txn = PaymentTransaction.objects.filter(
            id=serializer.validated_data["payment_transaction_id"],
            order__customer=request.user,
        ).first()
        if not txn:
            return api_error("Payment transaction not found")
        try:
            refund_obj = create_refund(
                transaction_obj=txn,
                amount=serializer.validated_data["amount"],
                reason=serializer.validated_data["reason"],
                idempotency_key=serializer.validated_data.get("idempotency_key", ""),
            )
        except PaymentProviderError as exc:
            return api_error(str(exc))
        return api_success(
            "Refund created successfully",
            {
                "refund_id": refund_obj.id,
                "provider_refund_id": refund_obj.provider_refund_id,
                "status": refund_obj.status,
            },
        )


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        signature = request.headers.get("Stripe-Signature", "")
        verified = verify_stripe_signature(payload, signature)
        if not verified:
            return api_error("Invalid webhook signature")

        event_id = request.data.get("id", "")
        event_type = request.data.get("type", "unknown")
        record_webhook("stripe", event_id, event_type, signature, verified=True)
        reconcile_stripe_event(request.data)
        return api_success("Webhook accepted")


class PayPalWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get("PayPal-Transmission-Sig", "")
        verified = verify_paypal_signature(signature)
        if not verified:
            return api_error("Invalid webhook signature")
        event_id = request.data.get("id", "")
        event_type = request.data.get("event_type", "unknown")
        record_webhook("paypal", event_id, event_type, signature, verified=True)
        reconcile_paypal_event(request.data)
        return api_success("Webhook accepted")
