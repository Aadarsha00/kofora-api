from rest_framework import serializers

from apps.users.models import User

from .models import Order, OrderAddressSnapshot, OrderItem, OrderStatusHistory


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


class AdminOrderCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone")


class OrderAddressSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAddressSnapshot
        fields = (
            "id",
            "address_type",
            "full_name",
            "phone",
            "company",
            "country",
            "state_province",
            "city",
            "postal_code",
            "address_line_1",
            "address_line_2",
        )


class AdminOrderListSerializer(serializers.ModelSerializer):
    customer = AdminOrderCustomerSerializer(read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "customer",
            "currency",
            "grand_total",
            "payment_status",
            "fulfillment_status",
            "item_count",
            "created_at",
            "updated_at",
        )

    def get_item_count(self, obj) -> int:
        return sum(item.quantity for item in obj.items.all())


class AdminOrderDetailSerializer(serializers.ModelSerializer):
    customer = AdminOrderCustomerSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    address_snapshots = OrderAddressSnapshotSerializer(many=True, read_only=True)

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
            "status_history",
            "address_snapshots",
        )


class AdminOrderStatusUpdateSerializer(serializers.Serializer):
    fulfillment_status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")
    staff_notes = serializers.CharField(required=False, allow_blank=True)
