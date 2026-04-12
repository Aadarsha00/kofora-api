from django.contrib import admin

from .models import InventoryAdjustment, LowStockAlert


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "quantity_delta", "reason", "reference", "created_at")
    list_filter = ("reason",)
    search_fields = ("variant__sku", "reference")


@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "threshold", "current_stock", "is_resolved", "created_at")
    list_filter = ("is_resolved",)
    search_fields = ("variant__sku",)
