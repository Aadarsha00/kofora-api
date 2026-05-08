from decimal import Decimal, ROUND_HALF_UP

from apps.discounts.services.discount_service import apply_coupon_to_amount

from ..models import Cart


MONEY_QUANT = Decimal("0.01")
TAX_RATE = Decimal("0.08")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_cart_totals(cart: Cart):
    subtotal = Decimal("0.00")
    for item in cart.variant_items.select_related("variant"):
        subtotal += item.variant.price * item.quantity
    for item in cart.bundle_items.select_related("bundle"):
        subtotal += item.bundle.bundle_price * item.quantity
    subtotal = _money(subtotal)

    discount = Decimal("0.00")
    if cart.applied_coupon:
        discount = apply_coupon_to_amount(cart.applied_coupon, subtotal)
    discount = _money(discount)

    shipping = Decimal("0.00")
    if cart.shipping_method:
        shipping = cart.shipping_method.base_rate
    shipping = _money(shipping)

    taxable_amount = subtotal - discount + shipping
    tax = _money(taxable_amount * TAX_RATE)
    total = _money(taxable_amount + tax)

    return {
        "subtotal": subtotal,
        "discount_amount": discount,
        "shipping_amount": shipping,
        "tax_amount": tax,
        "grand_total": total,
        "discount": discount,
        "shipping": shipping,
        "tax": tax,
        "total": total,
    }
