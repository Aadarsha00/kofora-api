from rest_framework import serializers

from .models import PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"


class StripeIntentRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    idempotency_key = serializers.CharField(max_length=120)


class StripeCheckoutRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    idempotency_key = serializers.CharField(max_length=120)
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()


class StripeCheckoutConfirmRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    provider_payment_id = serializers.CharField(max_length=150)


class PayPalOrderRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    idempotency_key = serializers.CharField(max_length=120)
    return_url = serializers.URLField()
    cancel_url = serializers.URLField()


class PayPalCaptureRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    provider_payment_id = serializers.CharField(max_length=150)
    payer_id = serializers.CharField(max_length=150)


class RefundRequestSerializer(serializers.Serializer):
    payment_transaction_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(max_length=255)
    idempotency_key = serializers.CharField(max_length=120, required=False, allow_blank=True)
