from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.cart.services.cart_service import calculate_cart_totals
from apps.discounts.services.discount_service import attach_discount_claim_to_order, validate_cart_discount_claim
from apps.inventory.services.inventory_service import InsufficientStockError
from apps.payments.models import PaymentTransaction

from ..models import Order, OrderAddressSnapshot, OrderItem, OrderStatusHistory
from .stock_service import release_reserved_stock_for_order, reserve_order_stock_from_cart


def generate_order_number() -> str:
    return f"KOF-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"


@transaction.atomic
def create_order_from_cart(cart, customer_notes: str = "") -> Order:
    is_valid, reason = validate_cart_discount_claim(cart)
    if not is_valid:
        raise ValueError(reason)

    totals = calculate_cart_totals(cart)
    order = Order.objects.create(
        order_number=generate_order_number(),
        customer=cart.user,
        currency=cart.currency,
        subtotal=totals["subtotal"],
        discount_amount=totals["discount_amount"],
        shipping_amount=totals["shipping_amount"],
        tax_amount=totals["tax_amount"],
        grand_total=totals["grand_total"],
        customer_notes=customer_notes,
        fulfillment_status=Order.STATUS_AWAITING_PAYMENT,
    )

    if cart.shipping_address:
        OrderAddressSnapshot.objects.create(
            order=order,
            address_type=OrderAddressSnapshot.TYPE_SHIPPING,
            full_name=cart.shipping_address.full_name,
            phone=cart.shipping_address.phone,
            company=cart.shipping_address.company,
            country=cart.shipping_address.country,
            state_province=cart.shipping_address.state_province,
            city=cart.shipping_address.city,
            postal_code=cart.shipping_address.postal_code,
            address_line_1=cart.shipping_address.address_line_1,
            address_line_2=cart.shipping_address.address_line_2,
        )
    if cart.billing_address:
        OrderAddressSnapshot.objects.create(
            order=order,
            address_type=OrderAddressSnapshot.TYPE_BILLING,
            full_name=cart.billing_address.full_name,
            phone=cart.billing_address.phone,
            company=cart.billing_address.company,
            country=cart.billing_address.country,
            state_province=cart.billing_address.state_province,
            city=cart.billing_address.city,
            postal_code=cart.billing_address.postal_code,
            address_line_1=cart.billing_address.address_line_1,
            address_line_2=cart.billing_address.address_line_2,
        )

    try:
        reserve_order_stock_from_cart(cart, order)
    except InsufficientStockError as exc:
        raise ValueError(str(exc)) from exc

    for item in cart.variant_items.select_related("variant", "variant__product"):
        OrderItem.objects.create(
            order=order,
            product_name=item.variant.product.name,
            variant_sku=item.variant.sku,
            size=item.variant.size,
            color=item.variant.color,
            quantity=item.quantity,
            unit_price=item.variant.price,
            discount_amount=0,
            line_total=item.variant.price * item.quantity,
        )

    for bundle_item in cart.bundle_items.select_related("bundle", "bundle__product"):
        OrderItem.objects.create(
            order=order,
            product_name=bundle_item.bundle.product.name,
            variant_sku=f"BUNDLE-{bundle_item.bundle.id}",
            size="bundle",
            color="bundle",
            quantity=bundle_item.quantity,
            unit_price=bundle_item.bundle.bundle_price,
            discount_amount=0,
            line_total=bundle_item.bundle.bundle_price * bundle_item.quantity,
        )

    OrderStatusHistory.objects.create(
        order=order,
        from_status="",
        to_status=Order.STATUS_AWAITING_PAYMENT,
        note="Order created from cart",
    )

    attach_discount_claim_to_order(cart, order)

    return order


@transaction.atomic
def update_order_status(order, *, to_status: str, changed_by=None, note: str = "", staff_notes=None) -> Order:
    valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}
    if to_status not in valid_statuses:
        raise ValueError("Invalid fulfillment status")

    from_status = order.fulfillment_status
    status_changed = to_status != from_status

    update_fields = ["updated_at"]
    if status_changed:
        order.fulfillment_status = to_status
        update_fields.append("fulfillment_status")
    if staff_notes is not None:
        order.staff_notes = staff_notes
        update_fields.append("staff_notes")

    order.save(update_fields=update_fields)

    if status_changed:
        if to_status == Order.STATUS_CANCELLED:
            release_reserved_stock_for_order(order)

        OrderStatusHistory.objects.create(
            order=order,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            note=note,
        )

    return order


def get_expirable_unpaid_orders(*, older_than_minutes: int | None = None, now=None):
    minutes = older_than_minutes or settings.ORDER_PAYMENT_RESERVATION_MINUTES
    cutoff = (now or timezone.now()) - timedelta(minutes=minutes)
    return Order.objects.filter(
        fulfillment_status=Order.STATUS_AWAITING_PAYMENT,
        payment_status="pending",
        created_at__lte=cutoff,
    )


@transaction.atomic
def expire_unpaid_orders(*, older_than_minutes: int | None = None) -> int:
    minutes = older_than_minutes or settings.ORDER_PAYMENT_RESERVATION_MINUTES
    expired_count = 0
    orders = list(get_expirable_unpaid_orders(older_than_minutes=minutes).select_for_update().order_by("created_at"))

    for order in orders:
        from_status = order.fulfillment_status
        release_reserved_stock_for_order(order)
        PaymentTransaction.objects.filter(
            order=order,
            status=PaymentTransaction.STATUS_PENDING,
        ).update(
            status=PaymentTransaction.STATUS_FAILED,
            failure_reason="Order expired before payment completed",
            updated_at=timezone.now(),
        )

        order.payment_status = "expired"
        order.fulfillment_status = Order.STATUS_CANCELLED
        order.save(update_fields=["payment_status", "fulfillment_status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order,
            from_status=from_status,
            to_status=Order.STATUS_CANCELLED,
            note=f"Payment window expired after {minutes} minutes; reserved stock released",
        )
        expired_count += 1

    return expired_count
