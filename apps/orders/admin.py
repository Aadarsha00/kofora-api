from django.contrib import admin

from .models import Order, OrderAddressSnapshot, OrderItem, OrderStatusHistory, RefundRecord, ReturnRecord


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_sku", "quantity", "unit_price", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "order_number", "customer", "currency", "grand_total", "payment_status", "fulfillment_status", "created_at")
    list_filter = ("currency", "payment_status", "fulfillment_status")
    search_fields = ("order_number", "customer__email")
    readonly_fields = ("order_number", "subtotal", "discount_amount", "shipping_amount", "tax_amount", "grand_total")
    inlines = [OrderItemInline]


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "from_status", "to_status", "changed_by", "created_at")
    list_filter = ("to_status",)


@admin.register(OrderAddressSnapshot)
class OrderAddressSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "address_type", "full_name", "country", "city")
    list_filter = ("address_type", "country")


@admin.register(RefundRecord)
class RefundRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "amount", "reason", "status", "created_at")


@admin.register(ReturnRecord)
class ReturnRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "reason", "status", "created_at")
