from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Order(TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_AWAITING_PAYMENT = "awaiting_payment"
    STATUS_PAID = "paid"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_PARTIALLY_REFUNDED = "partially_refunded"
    STATUS_REFUNDED = "refunded"
    STATUS_RETURNED = "returned"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_AWAITING_PAYMENT, "Awaiting Payment"),
        (STATUS_PAID, "Paid"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_PARTIALLY_REFUNDED, "Partially Refunded"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_RETURNED, "Returned"),
    )

    order_number = models.CharField(max_length=32, unique=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    currency = models.CharField(max_length=3)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(max_length=30, default="pending")
    fulfillment_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    customer_notes = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]


class OrderAddressSnapshot(TimeStampedModel):
    TYPE_BILLING = "billing"
    TYPE_SHIPPING = "shipping"

    TYPE_CHOICES = ((TYPE_BILLING, "Billing"), (TYPE_SHIPPING, "Shipping"))

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="address_snapshots")
    address_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    company = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=2)
    state_province = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "order_address_snapshots"


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=255)
    variant_sku = models.CharField(max_length=80)
    size = models.CharField(max_length=80)
    color = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "order_items"


class OrderStatusHistory(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "order_status_history"


class RefundRecord(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refund_records")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=30, default="pending")

    class Meta:
        db_table = "refund_records"


class ReturnRecord(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="return_records")
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=30, default="requested")

    class Meta:
        db_table = "return_records"
