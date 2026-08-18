"""Selects which buy-X-get-Y offers apply to a cart and what they are worth.

Split from `discount_service` so the ORM-facing glue stays separate from the
pure pricing engine in `bogo_service`.
"""

from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from ..models import Discount, DiscountRule, DiscountUsage
from .bogo_service import BogoConfig, CartLine, DiscountScope, compute_bogo_discount


def _scope_from_rules(rules, role: str) -> DiscountScope:
    product_ids, bundle_ids, category_ids = set(), set(), set()
    for rule in rules:
        if rule.role != role:
            continue
        if rule.product_id:
            product_ids.add(rule.product_id)
        if rule.bundle_id:
            bundle_ids.add(rule.bundle_id)
        if rule.category_id:
            category_ids.add(rule.category_id)
    return DiscountScope(
        product_ids=frozenset(product_ids),
        bundle_ids=frozenset(bundle_ids),
        category_ids=frozenset(category_ids),
    )


def build_cart_lines(cart) -> list[CartLine]:
    """Flatten a cart into the pricing engine's input.

    Prices come from the live variant/bundle records rather than anything stored
    on the cart row, so a price change between "add to cart" and checkout is
    reflected in the reward.
    """
    lines: list[CartLine] = []

    variant_items = cart.variant_items.select_related("variant", "variant__product").prefetch_related(
        "variant__product__categories"
    )
    for item in variant_items:
        product = item.variant.product
        lines.append(
            CartLine(
                key=f"variant:{item.id}",
                unit_price=item.variant.price,
                quantity=item.quantity,
                product_id=product.id,
                category_ids=frozenset(category.id for category in product.categories.all()),
            )
        )

    for item in cart.bundle_items.select_related("bundle"):
        lines.append(
            CartLine(
                key=f"bundle:{item.id}",
                unit_price=item.bundle.bundle_price,
                quantity=item.quantity,
                bundle_id=item.bundle_id,
            )
        )

    return lines


def config_from_discount(discount: Discount, rules=None) -> BogoConfig:
    rules = rules if rules is not None else list(discount.rules.all())
    reward_scope = _scope_from_rules(rules, DiscountRule.ROLE_REWARD)
    return BogoConfig(
        buy_quantity=discount.buy_quantity or 0,
        get_quantity=discount.get_quantity or 0,
        reward_percentage=discount.reward_percentage,
        max_applications=discount.max_applications,
        eligible_scope=_scope_from_rules(rules, DiscountRule.ROLE_ELIGIBLE),
        # An empty reward scope means "reward comes out of the eligible pool".
        reward_scope=None if reward_scope.is_empty else reward_scope,
    )


def eligible_bogo_discounts(subtotal: Decimal, user=None):
    """Active, in-window, auto-applied buy-X-get-Y discounts for this shopper.

    Only auto-applied offers are considered here — a bogo behind a coupon code is
    applied through the normal coupon path instead.
    """
    now = timezone.now()
    queryset = (
        Discount.objects.filter(
            discount_type=Discount.TYPE_BOGO,
            is_active=True,
            is_auto_applied=True,
        )
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))
        .filter(minimum_order_amount__lte=subtotal)
        .prefetch_related("rules")
    )

    usable = []
    for discount in queryset:
        if discount.usage_limit is not None:
            if DiscountUsage.objects.filter(discount=discount).count() >= discount.usage_limit:
                continue
        if user is not None and user.is_authenticated:
            if discount.per_user_limit is not None:
                if DiscountUsage.objects.filter(discount=discount, user=user).count() >= discount.per_user_limit:
                    continue
            if discount.first_order_only:
                from apps.orders.models import Order

                if Order.objects.filter(customer=user, payment_status="paid").exists():
                    continue
        elif discount.first_order_only:
            # Anonymous shoppers cannot be checked for a prior order; the claim
            # flow handles first-order offers, so skip them here.
            continue
        usable.append(discount)

    return usable


def best_bogo_for_cart(cart, subtotal: Decimal, user=None):
    """The single most valuable applicable offer, as (discount, BogoResult).

    Offers are not summed: two overlapping buy-X-get-Y promotions would otherwise
    both claim the same physical units and discount them twice. Picking the best
    one is the customer-favourable, merchant-safe resolution.
    """
    candidates = eligible_bogo_discounts(subtotal, user)
    if not candidates:
        return None, None

    lines = build_cart_lines(cart)
    if not lines:
        return None, None

    best_discount, best_result = None, None
    for discount in candidates:
        result = compute_bogo_discount(lines, config_from_discount(discount, list(discount.rules.all())))
        if not result.applies:
            continue
        if best_result is None or result.discount_amount > best_result.discount_amount:
            best_discount, best_result = discount, result

    return best_discount, best_result
