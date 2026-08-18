import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import Bundle, Product
from apps.subscriptions.models import SubscriptionPlan


class Discount(TimeStampedModel):
    TYPE_FLAT = "flat"
    TYPE_PERCENT = "percent"
    TYPE_BOGO = "bogo"

    TYPE_CHOICES = (
        (TYPE_FLAT, "Flat"),
        (TYPE_PERCENT, "Percent"),
        (TYPE_BOGO, "Buy X get Y"),
    )

    # Where the free/discounted units are taken from.
    REWARD_CHEAPEST = "cheapest"
    REWARD_SET = "reward_set"

    REWARD_SOURCE_CHOICES = (
        (REWARD_CHEAPEST, "Cheapest eligible items in the cart"),
        (REWARD_SET, "Items marked as reward on the discount rules"),
    )

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

    # --- Buy X get Y configuration (only meaningful when discount_type == bogo) ---
    # "Buy `buy_quantity`, get `get_quantity` at `reward_percentage` off."
    buy_quantity = models.PositiveIntegerField(null=True, blank=True)
    get_quantity = models.PositiveIntegerField(null=True, blank=True)
    # 100 = the reward units are free; 50 = half price. Lets one model cover
    # "buy 2 get 1 free" and "buy 2 get 1 half off" without a new type.
    reward_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("100.00"))
    # Cap how many times the offer repeats in a single cart. Null = unlimited.
    max_applications = models.PositiveIntegerField(null=True, blank=True)
    reward_source = models.CharField(max_length=20, choices=REWARD_SOURCE_CHOICES, default=REWARD_CHEAPEST)

    class Meta:
        db_table = "discounts"

    def __str__(self):
        return self.name

    @property
    def is_bogo(self) -> bool:
        return self.discount_type == self.TYPE_BOGO

    def clean(self):
        """Reject configurations the pricing engine cannot act on.

        Without this a "buy 0 get 1 free" discount would hand out unlimited free
        units, and a bogo discount with no reward quantity would silently never
        fire — both are far cheaper to catch at save time than in a live cart.
        """
        super().clean()
        errors = {}

        if self.discount_type == self.TYPE_FLAT and not self.flat_amount:
            errors["flat_amount"] = "A flat discount needs a flat amount."
        if self.discount_type == self.TYPE_PERCENT and not self.percentage:
            errors["percentage"] = "A percent discount needs a percentage."

        if self.discount_type == self.TYPE_BOGO:
            if not self.buy_quantity:
                errors["buy_quantity"] = "Buy quantity must be at least 1."
            if not self.get_quantity:
                errors["get_quantity"] = "Get quantity must be at least 1."
            if self.reward_percentage is None:
                errors["reward_percentage"] = "Reward percentage is required."
            elif not (Decimal("0") < self.reward_percentage <= Decimal("100")):
                errors["reward_percentage"] = "Reward percentage must be between 0 and 100."
            if self.max_applications is not None and self.max_applications < 1:
                errors["max_applications"] = "Max applications must be at least 1 when set."

        if self.starts_at and self.expires_at and self.starts_at >= self.expires_at:
            errors["expires_at"] = "Expiry must be after the start date."

        if errors:
            raise ValidationError(errors)


class CouponCode(TimeStampedModel):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="coupon_codes")
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coupon_codes"


class DiscountRule(TimeStampedModel):
    """Scopes a discount to part of the catalogue.

    A discount with no rules applies to the whole cart. `role` splits the rules
    into the set a customer must buy from and the set the reward is drawn from,
    which is what makes "buy 3 socks, get 1 cap free" expressible.
    """

    ROLE_ELIGIBLE = "eligible"
    ROLE_REWARD = "reward"

    ROLE_CHOICES = (
        (ROLE_ELIGIBLE, "Counts towards the buy quantity"),
        (ROLE_REWARD, "Can be given as the reward"),
    )

    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="rules")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE, related_name="discount_rules")
    bundle = models.ForeignKey(Bundle, null=True, blank=True, on_delete=models.CASCADE, related_name="discount_rules")
    subscription_plan = models.ForeignKey(SubscriptionPlan, null=True, blank=True, on_delete=models.CASCADE, related_name="discount_rules")
    category = models.ForeignKey("categories.Category", null=True, blank=True, on_delete=models.CASCADE, related_name="discount_rules")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ELIGIBLE)

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
