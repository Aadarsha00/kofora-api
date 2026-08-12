from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

from apps.discounts.services.discount_service import apply_coupon_to_amount
from apps.shipping.services.ups_client import UPSError
from apps.shipping.services.ups_service import get_rate_for_service

from ..models import Cart


MONEY_QUANT = Decimal("0.01")
WEIGHT_QUANT = Decimal("0.1")
TAX_RATE = Decimal("0.08")
GRAMS_PER_LB = Decimal("453.59237")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _cart_destination(cart: Cart):
    address = cart.shipping_address
    if not address:
        return None
    return {
        "full_name": address.full_name,
        "address_line_1": address.address_line_1,
        "address_line_2": address.address_line_2,
        "city": address.city,
        "state_province": address.state_province,
        "postal_code": address.postal_code,
        "country": address.country,
    }


def _cart_subtotal(cart: Cart) -> Decimal:
    subtotal = Decimal("0.00")
    for item in cart.variant_items.select_related("variant"):
        subtotal += item.variant.price * item.quantity
    for item in cart.bundle_items.select_related("bundle"):
        subtotal += item.bundle.bundle_price * item.quantity
    return _money(subtotal)


def _cart_weight_lbs(cart: Cart) -> Decimal:
    """Total shipment weight in pounds, using per-variant weight_grams where set
    and the configured default where not."""
    default_grams = settings.UPS_DEFAULT_ITEM_WEIGHT_GRAMS
    grams = 0
    for item in cart.variant_items.select_related("variant"):
        grams += (item.variant.weight_grams or default_grams) * item.quantity
    for item in cart.bundle_items.select_related("bundle"):
        bundle_grams = sum(
            (bi.variant.weight_grams or default_grams) * bi.quantity
            for bi in item.bundle.items.select_related("variant")
        )
        grams += (bundle_grams or default_grams) * item.quantity

    lbs = (Decimal(grams) / GRAMS_PER_LB).quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP)
    return max(lbs, Decimal(settings.UPS_MIN_PACKAGE_WEIGHT_LBS))


def resolve_shipping_amount(cart: Cart) -> Decimal:
    """Shipping cost for the cart's selected method.

    Free once the subtotal reaches the method's free_shipping_threshold.
    Otherwise: when the method is mapped to a UPS service and the cart has a
    domestic destination, this is a live UPS quote; otherwise (no method, no
    address, international, or any UPS failure) it falls back to the method's
    base_rate.
    """
    method = cart.shipping_method
    if not method:
        return Decimal("0.00")

    if method.free_shipping_threshold and _cart_subtotal(cart) >= method.free_shipping_threshold:
        return Decimal("0.00")

    service_code = (method.ups_service_code or "").strip()
    if not service_code:
        return method.base_rate

    destination = _cart_destination(cart)
    domestic = destination and (
        (destination.get("country") or "").upper()
        == settings.UPS_SHIPPER_COUNTRY.upper()
    )
    if not domestic:
        return method.base_rate

    try:
        return get_rate_for_service(
            destination,
            [{"weight": str(_cart_weight_lbs(cart))}],
            service_code,
        )
    except UPSError:
        return method.base_rate


def calculate_cart_totals(cart: Cart):
    subtotal = _cart_subtotal(cart)

    discount = Decimal("0.00")
    if cart.applied_coupon:
        discount = apply_coupon_to_amount(cart.applied_coupon, subtotal)
    discount = _money(discount)

    shipping = _money(resolve_shipping_amount(cart))

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
