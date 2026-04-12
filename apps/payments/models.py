from django.db import models

from apps.core.models import TimeStampedModel
from apps.orders.models import Order


class PaymentTransaction(TimeStampedModel):
    PROVIDER_STRIPE = "stripe"
    PROVIDER_PAYPAL = "paypal"

    PROVIDER_CHOICES = ((PROVIDER_STRIPE, "Stripe"), (PROVIDER_PAYPAL, "PayPal"))

    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = ((STATUS_PENDING, "Pending"), (STATUS_SUCCEEDED, "Succeeded"), (STATUS_FAILED, "Failed"))

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payment_transactions")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_payment_id = models.CharField(max_length=150, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    idempotency_key = models.CharField(max_length=120, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "payment_transactions"


class RefundTransaction(TimeStampedModel):
    payment_transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, related_name="refunds")
    provider_refund_id = models.CharField(max_length=150, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "refund_transactions"


class PaymentWebhookEvent(TimeStampedModel):
    provider = models.CharField(max_length=20, choices=PaymentTransaction.PROVIDER_CHOICES)
    event_id = models.CharField(max_length=150, unique=True)
    event_type = models.CharField(max_length=100)
    signature = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_webhook_events"
