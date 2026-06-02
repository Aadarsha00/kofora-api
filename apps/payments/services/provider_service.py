from decimal import Decimal

import paypalrestsdk
import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.cart.models import Cart
from apps.discounts.services.discount_service import redeem_discount_claim_for_order
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.services.stock_service import commit_reserved_stock_for_order

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


def _complete_paid_transaction(txn: PaymentTransaction, provider_reference_id: str = "") -> PaymentTransaction:
    was_succeeded = txn.status == PaymentTransaction.STATUS_SUCCEEDED
    was_paid = was_succeeded and txn.order.payment_status == "paid"
    previous_status = txn.order.fulfillment_status
    payment_window_expired = txn.order.payment_status == "expired" or (
        txn.order.fulfillment_status == Order.STATUS_CANCELLED and txn.order.payment_status != "paid"
    )
    txn.status = PaymentTransaction.STATUS_SUCCEEDED
    update_fields = ["status", "provider_reference_id", "updated_at"]
    if provider_reference_id:
        txn.provider_reference_id = provider_reference_id
    if payment_window_expired:
        txn.failure_reason = "Payment completed after order expired; manual review required"
        update_fields.append("failure_reason")
    txn.save(update_fields=update_fields)

    order = txn.order
    if payment_window_expired:
        if not was_succeeded:
            OrderStatusHistory.objects.create(
                order=order,
                from_status=previous_status,
                to_status=order.fulfillment_status,
                note="Payment confirmed after order expired; manual review required",
            )
        return txn

    if not was_paid:
        commit_reserved_stock_for_order(order)

    order.payment_status = "paid"
    order.fulfillment_status = Order.STATUS_PROCESSING
    order.save(update_fields=["payment_status", "fulfillment_status", "updated_at"])

    if not was_paid:
        redeem_discount_claim_for_order(order)
        OrderStatusHistory.objects.create(
            order=order,
            from_status=previous_status,
            to_status=Order.STATUS_PROCESSING,
            note="Payment confirmed; order moved to processing",
        )

    cart = Cart.objects.filter(user=order.customer).first()
    if cart:
        cart.variant_items.all().delete()
        cart.bundle_items.all().delete()
        cart.applied_coupon = None
        cart.applied_discount_claim = None
        cart.save(update_fields=["applied_coupon", "applied_discount_claim", "updated_at"])

    return txn


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
def create_stripe_checkout_session(order: Order, idempotency_key: str, success_url: str, cancel_url: str):
    _configure_providers()
    existing = _get_or_create_idempotent_txn(order, PaymentTransaction.PROVIDER_STRIPE, idempotency_key)
    if existing:
        return existing

    amount_cents = int(order.grand_total * Decimal("100"))
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            payment_method_types=["card"],
            client_reference_id=order.order_number,
            metadata={"order_number": order.order_number, "order_id": str(order.id)},
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": order.currency.lower(),
                        "unit_amount": amount_cents,
                        "product_data": {"name": f"Kofora order {order.order_number}"},
                    },
                }
            ],
            idempotency_key=idempotency_key or None,
        )
    except Exception as exc:
        raise PaymentProviderError(f"Stripe checkout creation failed: {exc}") from exc

    txn = PaymentTransaction.objects.create(
        order=order,
        provider=PaymentTransaction.PROVIDER_STRIPE,
        provider_payment_id=session["id"],
        provider_reference_id=getattr(session, "payment_intent", None) or "",
        checkout_url=session["url"],
        amount=order.grand_total,
        currency=order.currency,
        status=PaymentTransaction.STATUS_PENDING,
        idempotency_key=idempotency_key,
    )
    return txn


@transaction.atomic
def confirm_stripe_checkout_session(order: Order, provider_payment_id: str):
    _configure_providers()
    txn = PaymentTransaction.objects.filter(
        order=order,
        provider=PaymentTransaction.PROVIDER_STRIPE,
        provider_payment_id=provider_payment_id,
    ).first()
    if not txn:
        raise PaymentProviderError("Payment transaction not found")

    try:
        session = stripe.checkout.Session.retrieve(provider_payment_id)
    except Exception as exc:
        raise PaymentProviderError(f"Stripe checkout lookup failed: {exc}") from exc

    if getattr(session, "payment_status", "") != "paid":
        raise PaymentProviderError("Stripe payment has not been completed")

    return _complete_paid_transaction(
        txn,
        provider_reference_id=getattr(session, "payment_intent", None) or "",
    )


@transaction.atomic
def create_paypal_order(order: Order, idempotency_key: str, return_url: str, cancel_url: str):
    _configure_providers()
    existing = _get_or_create_idempotent_txn(order, PaymentTransaction.PROVIDER_PAYPAL, idempotency_key)
    if existing:
        return existing

    payload = {
        "intent": "SALE",
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

    approval_url = ""
    for link in paypal_payment.links:
        if getattr(link, "rel", "") == "approval_url":
            approval_url = getattr(link, "href", "")
            break

    txn = PaymentTransaction.objects.create(
        order=order,
        provider=PaymentTransaction.PROVIDER_PAYPAL,
        provider_payment_id=paypal_payment.id,
        checkout_url=approval_url,
        amount=order.grand_total,
        currency=order.currency,
        status=PaymentTransaction.STATUS_PENDING,
        idempotency_key=idempotency_key,
    )
    return txn


@transaction.atomic
def capture_paypal_order(order: Order, provider_payment_id: str, payer_id: str):
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

    if not paypal_payment.execute({"payer_id": payer_id}):
        txn.status = PaymentTransaction.STATUS_FAILED
        txn.failure_reason = str(paypal_payment.error)[:255]
        txn.save(update_fields=["status", "failure_reason", "updated_at"])
        raise PaymentProviderError("PayPal capture failed")

    return _complete_paid_transaction(txn)


@transaction.atomic
def create_refund(transaction_obj: PaymentTransaction, amount: Decimal, reason: str, idempotency_key: str = ""):
    _configure_providers()

    if transaction_obj.provider == PaymentTransaction.PROVIDER_STRIPE:
        try:
            payment_intent = transaction_obj.provider_reference_id or transaction_obj.provider_payment_id
            stripe_refund = stripe.Refund.create(
                payment_intent=payment_intent,
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
    event_object = (event_payload.get("data", {}) or {}).get("object", {})
    provider_payment_id = event_object.get("id")
    if not provider_payment_id:
        return
    txn = PaymentTransaction.objects.filter(
        provider=PaymentTransaction.PROVIDER_STRIPE,
        provider_payment_id=provider_payment_id,
    ).first()
    if not txn:
        txn = PaymentTransaction.objects.filter(
            provider=PaymentTransaction.PROVIDER_STRIPE,
            provider_reference_id=provider_payment_id,
        ).first()
    if not txn:
        return

    if event_type in {"payment_intent.succeeded", "checkout.session.completed"}:
        _complete_paid_transaction(txn, provider_reference_id=event_object.get("payment_intent", ""))
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
        _complete_paid_transaction(txn)
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
