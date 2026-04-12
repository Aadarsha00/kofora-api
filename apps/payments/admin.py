from django.contrib import admin

from .models import PaymentTransaction, PaymentWebhookEvent, RefundTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "provider", "provider_payment_id", "amount", "currency", "status")
    list_filter = ("provider", "status", "currency")
    search_fields = ("provider_payment_id", "order__order_number")


@admin.register(RefundTransaction)
class RefundTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_transaction", "provider_refund_id", "amount", "status")


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "event_id", "event_type", "is_verified", "processed_at")
    list_filter = ("provider", "is_verified", "event_type")
