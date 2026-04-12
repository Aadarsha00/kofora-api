from decimal import Decimal

from django.utils import timezone

from apps.orders.models import Order

from ..models import DiscountUsage


def apply_coupon_to_amount(coupon, subtotal):
    discount = coupon.discount
    if discount.discount_type == discount.TYPE_FLAT and discount.flat_amount:
        return min(discount.flat_amount, subtotal)
    if discount.discount_type == discount.TYPE_PERCENT and discount.percentage:
        return subtotal * (discount.percentage / Decimal("100.00"))
    return Decimal("0.00")


def validate_coupon_for_user(coupon, user, subtotal):
    if not coupon.is_active:
        return False, "Coupon is inactive"

    discount = coupon.discount
    now = timezone.now()
    if not discount.is_active:
        return False, "Discount is inactive"
    if discount.starts_at and now < discount.starts_at:
        return False, "Discount is not active yet"
    if discount.expires_at and now > discount.expires_at:
        return False, "Discount has expired"
    if subtotal < discount.minimum_order_amount:
        return False, "Minimum order amount is not met"

    if discount.usage_limit is not None:
        total_usage = DiscountUsage.objects.filter(discount=discount).count()
        if total_usage >= discount.usage_limit:
            return False, "Discount usage limit reached"

    if user and discount.per_user_limit is not None:
        user_usage = DiscountUsage.objects.filter(discount=discount, user=user).count()
        if user_usage >= discount.per_user_limit:
            return False, "Per-user usage limit reached"

    if user and discount.first_order_only:
        prior_orders = Order.objects.filter(customer=user).exclude(payment_status="cancelled").count()
        if prior_orders > 0:
            return False, "Coupon is valid for first order only"

    return True, "Coupon is valid"
