from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    interval_unit = models.CharField(max_length=20, default="month")
    interval_count = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    stripe_price_id = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscription_plans"


class CustomerSubscription(TimeStampedModel):
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    )

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="customer_subscriptions")
    stripe_subscription_id = models.CharField(max_length=120, unique=True)
    start_date = models.DateField()
    renewal_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    paused_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customer_subscriptions"


class SubscriptionEvent(TimeStampedModel):
    subscription = models.ForeignKey(CustomerSubscription, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=60)
    source = models.CharField(max_length=30, default="stripe")
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "subscription_events"
