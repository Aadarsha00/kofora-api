from django.db import models

from apps.core.models import TimeStampedModel


class ShippingZone(TimeStampedModel):
    name = models.CharField(max_length=120)
    country_code = models.CharField(max_length=2)
    state_code = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "shipping_zones"


class ShippingMethod(TimeStampedModel):
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name="methods")
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=60, unique=True)
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "shipping_methods"


class ShippingRateRule(TimeStampedModel):
    method = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE, related_name="rate_rules")
    min_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "shipping_rate_rules"
