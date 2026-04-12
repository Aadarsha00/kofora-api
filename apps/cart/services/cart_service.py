from decimal import Decimal

from apps.discounts.services.discount_service import apply_coupon_to_amount

from ..models import Cart


def calculate_cart_totals(cart: Cart):
    subtotal = Decimal("0.00")
    for item in cart.variant_items.select_related("variant"):
        subtotal += item.variant.price * item.quantity
    for item in cart.bundle_items.select_related("bundle"):
        subtotal += item.bundle.bundle_price * item.quantity

    discount_amount = Decimal("0.00")
    if cart.applied_coupon:
        discount_amount = apply_coupon_to_amount(cart.applied_coupon, subtotal)

    shipping_amount = Decimal("0.00")
    if cart.shipping_method:
        shipping_amount = cart.shipping_method.base_rate

    taxable_amount = subtotal - discount_amount + shipping_amount
    tax_amount = taxable_amount * Decimal("0.08")
    total = taxable_amount + tax_amount

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "shipping_amount": shipping_amount,
        "tax_amount": tax_amount,
        "grand_total": total,
    }
