from django.db.models import Count, Sum

from apps.orders.models import Order


def revenue_summary():
    paid_orders = Order.objects.filter(payment_status="paid")
    data = paid_orders.aggregate(total_revenue=Sum("grand_total"), order_count=Count("id"))
    order_count = data.get("order_count") or 0
    total_revenue = data.get("total_revenue") or 0
    average_order_value = (total_revenue / order_count) if order_count else 0
    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "average_order_value": average_order_value,
    }
