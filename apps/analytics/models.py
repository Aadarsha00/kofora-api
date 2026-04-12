from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import Product, ProductVariant


class EventType(TimeStampedModel):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    is_funnel_step = models.BooleanField(default=False)

    class Meta:
        db_table = "analytics_event_types"


class CustomerEvent(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events")
    event_type = models.ForeignKey(EventType, on_delete=models.PROTECT, related_name="events")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=80, blank=True)

    class Meta:
        db_table = "analytics_customer_events"


class DailyMetric(TimeStampedModel):
    metric_date = models.DateField(unique=True)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    order_count = models.PositiveIntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    repeat_customer_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "analytics_daily_metrics"
