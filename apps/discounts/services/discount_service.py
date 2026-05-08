from decimal import Decimal

from django.utils import timezone
from django.db import IntegrityError
from django.utils.crypto import constant_time_compare

from apps.orders.models import Order

from ..models import DiscountUsage, Discount, CouponCode, DiscountClaim


FIRST_ORDER_CLAIM_DAYS = 14


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
        if Order.objects.filter(customer=user, payment_status="paid").exists():
            return False, "Coupon is valid for first order only"

    return True, "Coupon is valid"


def _normalize_email(email: str) -> str:
    return (email or "").lower().strip()


def _get_first_order_coupon():
    discount = Discount.objects.filter(first_order_only=True, is_active=True).first()
    if not discount:
        return None, None
    coupon = CouponCode.objects.filter(discount=discount, is_active=True).first()
    return discount, coupon


def apply_first_order_discount(email: str):
    """
    Check if email is eligible for first-order discount.
    Returns: (success: bool, message: str, claim: DiscountClaim or None)
    
    Note: This does NOT mark the discount as used. Usage is tracked only after
    the order is successfully placed. This prevents blocking users who haven't completed purchase.
    """
    email = _normalize_email(email)
    
    discount, coupon = _get_first_order_coupon()
    if not discount:
        return False, "First-order discount not available", None
    if not coupon:
        return False, "No active first-order discount is available", None
    
    # Check if email already completed an order with this discount
    if DiscountUsage.objects.filter(discount=discount, email=email).exists():
        return False, "This email has already used the first-order discount", None
    
    now = timezone.now()
    DiscountClaim.objects.filter(
        discount=discount,
        email=email,
        status__in=[DiscountClaim.STATUS_CLAIMED, DiscountClaim.STATUS_APPLIED],
        expires_at__lte=now,
    ).update(status=DiscountClaim.STATUS_EXPIRED)

    existing_claim = (
        DiscountClaim.objects.filter(
            discount=discount,
            email=email,
            status__in=[DiscountClaim.STATUS_CLAIMED, DiscountClaim.STATUS_APPLIED],
            expires_at__gt=now,
        )
        .order_by("-created_at")
        .first()
    )
    if existing_claim:
        return True, "First-order discount available", existing_claim

    claim = DiscountClaim.objects.create(
        discount=discount,
        coupon_code=coupon,
        email=email,
        expires_at=now + timezone.timedelta(days=FIRST_ORDER_CLAIM_DAYS),
    )
    return True, "First-order discount available", claim


def validate_discount_claim_for_user(claim: DiscountClaim, user, subtotal: Decimal):
    now = timezone.now()
    if not claim:
        return False, "Discount claim not found"
    if claim.status not in [DiscountClaim.STATUS_CLAIMED, DiscountClaim.STATUS_APPLIED]:
        return False, "Discount claim is no longer available"
    if claim.expires_at <= now:
        claim.status = DiscountClaim.STATUS_EXPIRED
        claim.save(update_fields=["status", "updated_at"])
        return False, "Discount claim has expired"
    if not constant_time_compare(_normalize_email(claim.email), _normalize_email(user.email)):
        return False, "Discount email must match the logged-in account"
    if Order.objects.filter(customer=user, payment_status="paid").exists():
        return False, "First-order discount is only available before your first paid order"
    if not claim.coupon_code or not claim.coupon_code.is_active:
        return False, "Discount code is no longer active"

    is_valid, reason = validate_coupon_for_user(claim.coupon_code, user, subtotal)
    if not is_valid:
        return False, reason

    return True, "Discount claim is valid"


def _cart_subtotal(cart) -> Decimal:
    subtotal = Decimal("0.00")
    for item in cart.variant_items.select_related("variant"):
        subtotal += item.variant.price * item.quantity
    for item in cart.bundle_items.select_related("bundle"):
        subtotal += item.bundle.bundle_price * item.quantity
    return subtotal


def apply_first_order_claim_to_cart(token: str, user, cart):
    claim = DiscountClaim.objects.select_related("discount", "coupon_code").filter(token=token).first()
    is_valid, reason = validate_discount_claim_for_user(claim, user, _cart_subtotal(cart))
    if not is_valid:
        return False, reason, None

    claim.user = user
    claim.status = DiscountClaim.STATUS_APPLIED
    claim.applied_at = timezone.now()
    claim.save(update_fields=["user", "status", "applied_at", "updated_at"])

    cart.applied_coupon = claim.coupon_code
    cart.applied_discount_claim = claim
    cart.save(update_fields=["applied_coupon", "applied_discount_claim", "updated_at"])

    return True, "First-order discount applied", cart


def validate_cart_discount_claim(cart):
    claim = getattr(cart, "applied_discount_claim", None)
    if not claim:
        return True, "No first-order discount claim applied"
    return validate_discount_claim_for_user(claim, cart.user, _cart_subtotal(cart))


def attach_discount_claim_to_order(cart, order):
    claim = getattr(cart, "applied_discount_claim", None)
    if not claim:
        return
    claim.order = order
    claim.status = DiscountClaim.STATUS_APPLIED
    claim.save(update_fields=["order", "status", "updated_at"])


def redeem_discount_claim_for_order(order):
    claim = DiscountClaim.objects.select_related("coupon_code", "discount").filter(order=order).first()
    if not claim or claim.status == DiscountClaim.STATUS_REDEEMED:
        return False

    claim.status = DiscountClaim.STATUS_REDEEMED
    claim.redeemed_at = timezone.now()
    claim.save(update_fields=["status", "redeemed_at", "updated_at"])

    track_discount_usage(
        email=claim.email,
        coupon_code=claim.coupon_code,
        order_id=order.order_number,
        user=order.customer,
    )
    return True


def track_discount_usage(email: str, coupon_code: CouponCode, order_id: str = "", user=None):
    """
    Track discount usage after order is placed.
    This is called when order creation is complete.
    """
    email = _normalize_email(email)
    discount = coupon_code.discount
    
    try:
        DiscountUsage.objects.create(
            discount=discount,
            user=user,
            email=email,
            coupon_code=coupon_code,
            order_id=order_id
        )
        return True
    except IntegrityError:
        # Email already tracked for this discount (shouldn't happen if logic is correct)
        return False
