from celery import shared_task

from apps.notifications.tasks.email_tasks import send_email_task
from apps.products.models import ProductVariant

from ..models import LowStockAlert


@shared_task
def detect_low_stock_task():
    variants = ProductVariant.objects.filter(is_active=True)
    for variant in variants:
        if variant.available_quantity <= variant.low_stock_threshold:
            alert, created = LowStockAlert.objects.get_or_create(
                variant=variant,
                threshold=variant.low_stock_threshold,
                current_stock=variant.available_quantity,
                is_resolved=False,
            )
            if created:
                send_email_task.delay(
                    subject="Low stock alert",
                    body=f"Variant {variant.sku} is low on stock: {variant.available_quantity}",
                    recipient="ops@kofora.com",
                )
