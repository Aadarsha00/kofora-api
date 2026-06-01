from django.db.models import Count, F, Sum

from apps.orders.models import Order
from apps.products.models import Product, ProductVariant
from apps.users.models import User


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


def dashboard_summary():
    paid_orders = Order.objects.filter(payment_status="paid")
    total_revenue = paid_orders.aggregate(total=Sum("grand_total")).get("total") or 0
    paid_count = paid_orders.count()
    total_orders = Order.objects.count()

    status_rows = Order.objects.values("fulfillment_status").annotate(count=Count("id"))
    orders_by_status = {row["fulfillment_status"]: row["count"] for row in status_rows}
    awaiting_fulfillment = Order.objects.filter(
        fulfillment_status__in=[Order.STATUS_PAID, Order.STATUS_PROCESSING]
    ).count()

    recent_orders = [
        {
            "id": order.id,
            "order_number": order.order_number,
            "customer_email": order.customer.email,
            "grand_total": order.grand_total,
            "currency": order.currency,
            "payment_status": order.payment_status,
            "fulfillment_status": order.fulfillment_status,
            "created_at": order.created_at,
        }
        for order in Order.objects.select_related("customer").order_by("-created_at")[:6]
    ]

    low_stock_qs = (
        ProductVariant.objects.select_related("product")
        .annotate(available=F("stock_quantity") - F("reserved_quantity"))
        .filter(is_active=True, available__lte=F("low_stock_threshold"))
        .order_by("available")
    )
    low_stock_count = low_stock_qs.count()
    low_stock = [
        {
            "id": variant.id,
            "product_id": variant.product_id,
            "product_name": variant.product.name,
            "sku": variant.sku,
            "size": variant.size,
            "color": variant.color,
            "available": max(variant.stock_quantity - variant.reserved_quantity, 0),
            "low_stock_threshold": variant.low_stock_threshold,
        }
        for variant in low_stock_qs[:8]
    ]

    return {
        "revenue": {
            "total_revenue": total_revenue,
            "paid_orders": paid_count,
            "average_order_value": (total_revenue / paid_count) if paid_count else 0,
        },
        "orders": {
            "total": total_orders,
            "awaiting_fulfillment": awaiting_fulfillment,
            "by_status": orders_by_status,
        },
        "catalog": {
            "product_count": Product.objects.count(),
            "published_count": Product.objects.filter(is_published=True).count(),
            "low_stock_count": low_stock_count,
        },
        "customers": {
            "total": User.objects.filter(role=User.ROLE_CUSTOMER).count(),
        },
        "recent_orders": recent_orders,
        "low_stock": low_stock,
    }
