import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import Bundle, Product
from apps.subscriptions.models import SubscriptionPlan


class Discount(TimeStampedModel):
    TYPE_FLAT = "flat"
    TYPE_PERCENT = "percent"

    TYPE_CHOICES = ((TYPE_FLAT, "Flat"), (TYPE_PERCENT, "Percent"))

    name = models.CharField(max_length=150)
    discount_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    flat_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    first_order_only = models.BooleanField(default=False)
    is_auto_applied = models.BooleanField(default=False)
    is_stackable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "discounts"


class CouponCode(TimeStampedModel):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="coupon_codes")
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coupon_codes"


class DiscountRule(TimeStampedModel):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="rules")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE, related_name="discount_rules")
    bundle = models.ForeignKey(Bundle, null=True, blank=True, on_delete=models.CASCADE, related_name="discount_rules")
    subscription_plan = models.ForeignKey(SubscriptionPlan, null=True, blank=True, on_delete=models.CASCADE, related_name="discount_rules")

    class Meta:
        db_table = "discount_rules"


class DiscountUsage(TimeStampedModel):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="discount_usages", null=True, blank=True)
    coupon_code = models.ForeignKey(CouponCode, null=True, blank=True, on_delete=models.SET_NULL)
    order_id = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)  # Track email for first-order discounts without auth

    class Meta:
        db_table = "discount_usages"
        # Prevent duplicate usage of first-order discount per email
        unique_together = [("discount", "email")]


class DiscountClaim(TimeStampedModel):
    STATUS_CLAIMED = "claimed"
    STATUS_APPLIED = "applied"
    STATUS_REDEEMED = "redeemed"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = (
        (STATUS_CLAIMED, "Claimed"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_REDEEMED, "Redeemed"),
        (STATUS_EXPIRED, "Expired"),
    )

    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="claims")
    coupon_code = models.ForeignKey(CouponCode, null=True, blank=True, on_delete=models.SET_NULL, related_name="claims")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="discount_claims")
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="discount_claims")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CLAIMED)
    expires_at = models.DateTimeField()
    applied_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "discount_claims"
        indexes = [
            models.Index(fields=["discount", "email", "status"]),
            models.Index(fields=["token", "status"]),
        ]
