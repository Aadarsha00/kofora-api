from django.db import transaction
from django.db.models import F

from apps.products.models import ProductVariant

from ..models import InventoryAdjustment


class InsufficientStockError(Exception):
    pass


@transaction.atomic
def reserve_stock(variant_id: int, quantity: int, reference: str) -> None:
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
    if variant.available_quantity < quantity:
        raise InsufficientStockError("Insufficient stock")
    variant.reserved_quantity = F("reserved_quantity") + quantity
    variant.save(update_fields=["reserved_quantity", "updated_at"])
    InventoryAdjustment.objects.create(
        variant=variant,
        quantity_delta=-quantity,
        reason=InventoryAdjustment.REASON_ORDER,
        reference=reference,
        notes="Reserved stock",
    )


@transaction.atomic
def commit_stock(variant_id: int, quantity: int, reference: str) -> None:
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
    if variant.reserved_quantity < quantity:
        raise InsufficientStockError("Insufficient reserved stock")
    if variant.stock_quantity < quantity:
        raise InsufficientStockError("Insufficient stock")
    variant.stock_quantity = F("stock_quantity") - quantity
    variant.reserved_quantity = F("reserved_quantity") - quantity
    variant.save(update_fields=["stock_quantity", "reserved_quantity", "updated_at"])
    InventoryAdjustment.objects.create(
        variant=variant,
        quantity_delta=-quantity,
        reason=InventoryAdjustment.REASON_ORDER,
        reference=reference,
        notes="Committed stock",
    )


@transaction.atomic
def release_reserved_stock(variant_id: int, quantity: int, reference: str, reason: str) -> None:
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
    if variant.reserved_quantity < quantity:
        raise InsufficientStockError("Insufficient reserved stock")
    variant.reserved_quantity = F("reserved_quantity") - quantity
    variant.save(update_fields=["reserved_quantity", "updated_at"])
    InventoryAdjustment.objects.create(
        variant=variant,
        quantity_delta=quantity,
        reason=reason,
        reference=reference,
        notes="Released reserved stock",
    )
