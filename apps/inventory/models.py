from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import ProductVariant


class InventoryAdjustment(TimeStampedModel):
    REASON_MANUAL = "manual"
    REASON_ORDER = "order"
    REASON_CANCELLATION = "cancellation"
    REASON_REFUND = "refund"

    REASON_CHOICES = (
        (REASON_MANUAL, "Manual"),
        (REASON_ORDER, "Order"),
        (REASON_CANCELLATION, "Cancellation"),
        (REASON_REFUND, "Refund"),
    )

    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="inventory_adjustments")
    quantity_delta = models.IntegerField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    adjusted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "inventory_adjustments"
        ordering = ["-created_at"]


class LowStockAlert(TimeStampedModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="low_stock_alerts")
    threshold = models.PositiveIntegerField()
    current_stock = models.PositiveIntegerField()
    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "low_stock_alerts"
