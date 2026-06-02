from collections import defaultdict

from django.db import transaction
from django.db.models import Sum

from apps.inventory.models import InventoryAdjustment
from apps.inventory.services.inventory_service import commit_stock, release_reserved_stock, reserve_stock


RESERVED_STOCK_NOTE = "Reserved stock"
COMMITTED_STOCK_NOTE = "Committed stock"
RELEASED_STOCK_NOTE = "Released reserved stock"


def _cart_stock_requirements(cart) -> dict[int, int]:
    quantities = defaultdict(int)

    for item in cart.variant_items.select_related("variant"):
        quantities[item.variant_id] += item.quantity

    bundle_items = cart.bundle_items.select_related("bundle").prefetch_related("bundle__items")
    for cart_bundle_item in bundle_items:
        for bundle_component in cart_bundle_item.bundle.items.all():
            quantities[bundle_component.variant_id] += bundle_component.quantity * cart_bundle_item.quantity

    return dict(quantities)


def _has_order_stock_adjustment(order, note: str) -> bool:
    return InventoryAdjustment.objects.filter(
        reference=order.order_number,
        notes=note,
    ).exists()


def _reserved_stock_lines(order) -> list[dict[str, int]]:
    rows = (
        InventoryAdjustment.objects.filter(
            reason=InventoryAdjustment.REASON_ORDER,
            reference=order.order_number,
            notes=RESERVED_STOCK_NOTE,
            quantity_delta__lt=0,
        )
        .values("variant_id")
        .annotate(total_delta=Sum("quantity_delta"))
    )

    return [
        {"variant_id": row["variant_id"], "quantity": -row["total_delta"]}
        for row in rows
        if row["total_delta"] < 0
    ]


@transaction.atomic
def reserve_order_stock_from_cart(cart, order) -> None:
    for variant_id, quantity in sorted(_cart_stock_requirements(cart).items()):
        reserve_stock(variant_id, quantity, order.order_number)


@transaction.atomic
def commit_reserved_stock_for_order(order) -> None:
    if _has_order_stock_adjustment(order, COMMITTED_STOCK_NOTE):
        return

    for line in _reserved_stock_lines(order):
        commit_stock(line["variant_id"], line["quantity"], order.order_number)


@transaction.atomic
def release_reserved_stock_for_order(order, reason: str = InventoryAdjustment.REASON_CANCELLATION) -> None:
    if _has_order_stock_adjustment(order, COMMITTED_STOCK_NOTE):
        return
    if _has_order_stock_adjustment(order, RELEASED_STOCK_NOTE):
        return

    for line in _reserved_stock_lines(order):
        release_reserved_stock(line["variant_id"], line["quantity"], order.order_number, reason)
