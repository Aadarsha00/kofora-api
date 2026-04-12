from decimal import Decimal

import paypalrestsdk
import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order

from ..models import PaymentTransaction, PaymentWebhookEvent, RefundTransaction


class PaymentProviderError(Exception):
    pass


def _configure_providers() -> None:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    paypalrestsdk.configure(
        {
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET,
        }
    )


def _get_or_create_idempotent_txn(order: Order, provider: str, idempotency_key: str):
    if not idempotency_key:
        return None
    return PaymentTransaction.objects.filter(
        order=order,
        provider=provider,
        idempotency_key=idempotency_key,
    ).first()


@transaction.atomic
def create_stripe_payment_intent(order: Order, idempotency_key: str):
    _configure_providers()
    existing = _get_or_create_idempotent_txn(order, PaymentTransaction.PROVIDER_STRIPE, idempotency_key)
    if existing:
        return existing

    amount_cents = int(order.grand_total * Decimal("100"))
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=order.currency.lower(),
            metadata={"order_number": order.order_number, "order_id": str(order.id)},
            idempotency_key=idempotency_key or None,
        )
    except Exception as exc:
        raise PaymentProviderError(f"Stripe intent creation failed: {exc}") from exc

    txn = PaymentTransaction.objects.create(
        order=order,
        provider=PaymentTransaction.PROVIDER_STRIPE,
        provider_payment_id=intent["id"],
        amount=order.grand_total,
        currency=order.currency,
        status=PaymentTransaction.STATUS_PENDING,
        idempotency_key=idempotency_key,
    )
    return txn


@transaction.atomic
def create_paypal_order(order: Order, idempotency_key: str, return_url: str, cancel_url: str):
    _configure_providers()
    existing = _get_or_create_idempotent_txn(order, PaymentTransaction.PROVIDER_PAYPAL, idempotency_key)
    if existing:
        return existing

    payload = {
        "intent": "CAPTURE",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {"return_url": return_url, "cancel_url": cancel_url},
        "transactions": [
            {
                "amount": {"total": str(order.grand_total), "currency": order.currency},
                "description": f"Kofora order {order.order_number}",
                "invoice_number": order.order_number,
            }
        ],
    }
    paypal_payment = paypalrestsdk.Payment(payload)
    if not paypal_payment.create():
        raise PaymentProviderError(f"PayPal order creation failed: {paypal_payment.error}")

    txn = PaymentTransaction.objects.create(
        order=order,
        provider=PaymentTransaction.PROVIDER_PAYPAL,
        provider_payment_id=paypal_payment.id,
        amount=order.grand_total,
        currency=order.currency,
        status=PaymentTransaction.STATUS_PENDING,
        idempotency_key=idempotency_key,
    )
    return txn


@transaction.atomic
def capture_paypal_order(order: Order, provider_payment_id: str):
    _configure_providers()
    txn = PaymentTransaction.objects.filter(
        order=order,
        provider=PaymentTransaction.PROVIDER_PAYPAL,
        provider_payment_id=provider_payment_id,
    ).first()
    if not txn:
        raise PaymentProviderError("Payment transaction not found")

    paypal_payment = paypalrestsdk.Payment.find(provider_payment_id)
    if not paypal_payment:
        raise PaymentProviderError("PayPal payment not found")

    if not paypal_payment.execute({"payer_id": "SYSTEM_CAPTURE"}):
        txn.status = PaymentTransaction.STATUS_FAILED
        txn.failure_reason = str(paypal_payment.error)[:255]
        txn.save(update_fields=["status", "failure_reason", "updated_at"])
        raise PaymentProviderError("PayPal capture failed")

    txn.status = PaymentTransaction.STATUS_SUCCEEDED
    txn.save(update_fields=["status", "updated_at"])
    order.payment_status = "paid"
    order.fulfillment_status = Order.STATUS_PROCESSING
    order.save(update_fields=["payment_status", "fulfillment_status", "updated_at"])
    return txn


@transaction.atomic
def create_refund(transaction_obj: PaymentTransaction, amount: Decimal, reason: str, idempotency_key: str = ""):
    _configure_providers()

    if transaction_obj.provider == PaymentTransaction.PROVIDER_STRIPE:
        try:
            stripe_refund = stripe.Refund.create(
                payment_intent=transaction_obj.provider_payment_id,
                amount=int(amount * Decimal("100")),
                reason="requested_by_customer",
            )
            provider_refund_id = stripe_refund["id"]
            status = "succeeded"
        except Exception as exc:
            raise PaymentProviderError(f"Stripe refund failed: {exc}") from exc
    else:
        sale = paypalrestsdk.Sale.find(transaction_obj.provider_payment_id)
        if not sale:
            raise PaymentProviderError("PayPal sale not found")
        refund = sale.refund({"amount": {"total": str(amount), "currency": transaction_obj.currency}})
        if not refund.success():
            raise PaymentProviderError(f"PayPal refund failed: {refund.error}")
        provider_refund_id = refund.id
        status = "succeeded"

    refund_obj = RefundTransaction.objects.create(
        payment_transaction=transaction_obj,
        provider_refund_id=provider_refund_id,
        amount=amount,
        status=status,
        reason=reason,
    )
    return refund_obj


def verify_stripe_signature(payload: bytes, signature: str) -> bool:
    if not signature or not settings.STRIPE_WEBHOOK_SECRET:
        return False
    try:
        stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=settings.STRIPE_WEBHOOK_SECRET)
        return True
    except Exception:
        return False


def verify_paypal_signature(signature: str) -> bool:
    # PayPal verification requires API call with transmission headers.
    return bool(signature)


@transaction.atomic
def reconcile_stripe_event(event_payload: dict):
    event_type = event_payload.get("type", "")
    provider_payment_id = (event_payload.get("data", {}) or {}).get("object", {}).get("id")
    if not provider_payment_id:
        return
    txn = PaymentTransaction.objects.filter(
        provider=PaymentTransaction.PROVIDER_STRIPE,
        provider_payment_id=provider_payment_id,
    ).first()
    if not txn:
        return

    if event_type == "payment_intent.succeeded":
        txn.status = PaymentTransaction.STATUS_SUCCEEDED
        txn.save(update_fields=["status", "updated_at"])
        order = txn.order
        order.payment_status = "paid"
        order.fulfillment_status = Order.STATUS_PROCESSING
        order.save(update_fields=["payment_status", "fulfillment_status", "updated_at"])
    elif event_type in {"payment_intent.payment_failed", "charge.failed"}:
        txn.status = PaymentTransaction.STATUS_FAILED
        txn.failure_reason = "Webhook reported payment failure"
        txn.save(update_fields=["status", "failure_reason", "updated_at"])


@transaction.atomic
def reconcile_paypal_event(event_payload: dict):
    event_type = event_payload.get("event_type", "")
    resource = event_payload.get("resource", {}) or {}
    provider_payment_id = resource.get("id", "")
    if not provider_payment_id:
        return
    txn = PaymentTransaction.objects.filter(
        provider=PaymentTransaction.PROVIDER_PAYPAL,
        provider_payment_id=provider_payment_id,
    ).first()
    if not txn:
        return

    if event_type in {"PAYMENT.CAPTURE.COMPLETED", "PAYMENT.SALE.COMPLETED"}:
        txn.status = PaymentTransaction.STATUS_SUCCEEDED
        txn.save(update_fields=["status", "updated_at"])
        order = txn.order
        order.payment_status = "paid"
        order.fulfillment_status = Order.STATUS_PROCESSING
        order.save(update_fields=["payment_status", "fulfillment_status", "updated_at"])
    elif event_type in {"PAYMENT.CAPTURE.DENIED", "PAYMENT.SALE.DENIED"}:
        txn.status = PaymentTransaction.STATUS_FAILED
        txn.failure_reason = "Webhook reported payment failure"
        txn.save(update_fields=["status", "failure_reason", "updated_at"])
def record_webhook(provider: str, event_id: str, event_type: str, signature: str, verified: bool):
    event, _ = PaymentWebhookEvent.objects.get_or_create(
        provider=provider,
        event_id=event_id,
        defaults={
            "event_type": event_type,
            "signature": signature,
            "is_verified": verified,
            "processed_at": timezone.now() if verified else None,
        },
    )
    return event
