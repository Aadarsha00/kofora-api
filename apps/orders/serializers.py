from rest_framework import serializers

from .models import Order, OrderItem, OrderStatusHistory


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "variant_sku",
            "size",
            "color",
            "quantity",
            "unit_price",
            "discount_amount",
            "line_total",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "customer",
            "currency",
            "subtotal",
            "discount_amount",
            "shipping_amount",
            "tax_amount",
            "grand_total",
            "payment_status",
            "fulfillment_status",
            "customer_notes",
            "staff_notes",
            "created_at",
            "updated_at",
            "items",
        )


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "note",
            "created_at",
        )


class OrderDetailSerializer(OrderSerializer):
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ("status_history",)
