from celery import shared_task

from apps.orders.services.order_service import expire_unpaid_orders


@shared_task(name="apps.orders.expire_unpaid_orders")
def expire_unpaid_orders_task() -> int:
    return expire_unpaid_orders()
