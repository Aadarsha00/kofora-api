from django.db import models

from apps.core.models import TimeStampedModel


class ShippingZone(TimeStampedModel):
    name = models.CharField(max_length=120)
    country_code = models.CharField(max_length=2)
    state_code = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "shipping_zones"

    def __str__(self):
        location = self.country_code
        if self.state_code:
            location = f"{location}-{self.state_code}"
        return f"{self.name} ({location})"


class ShippingMethod(TimeStampedModel):
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name="methods")
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=60, unique=True)
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "shipping_methods"

    def __str__(self):
        return f"{self.name} ({self.code})"


class ShippingRateRule(TimeStampedModel):
    method = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE, related_name="rate_rules")
    min_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "shipping_rate_rules"

    def __str__(self):
        upper = self.max_subtotal if self.max_subtotal is not None else "and up"
        return f"{self.method}: {self.min_subtotal} - {upper}"


class InternationalShipping(TimeStampedModel):
    CURRENCY_USD = "USD"
    CURRENCY_CAD = "CAD"
    CURRENCY_CHOICES = ((CURRENCY_USD, "USD"), (CURRENCY_CAD, "CAD"))

    DUTIES_CUSTOMER = "customer"
    DUTIES_MERCHANT = "merchant"
    DUTIES_INCLUDED = "included"
    DUTIES_CHOICES = (
        (DUTIES_CUSTOMER, "Customer pays duties/taxes"),
        (DUTIES_MERCHANT, "Merchant pays duties/taxes"),
        (DUTIES_INCLUDED, "Duties/taxes included"),
    )

    title = models.CharField(max_length=160)
    zone = models.ForeignKey(
        ShippingZone,
        on_delete=models.PROTECT,
        related_name="international_shipping_options",
        null=True,
        blank=True,
    )
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.SET_NULL,
        related_name="international_shipping_options",
        null=True,
        blank=True,
    )
    destination_country = models.CharField(max_length=120)
    destination_country_code = models.CharField(max_length=2, blank=True)
    destination_region = models.CharField(max_length=120, blank=True)
    service_name = models.CharField(max_length=120)
    carrier = models.CharField(max_length=120, blank=True)
    delivery_time = models.CharField(max_length=120, blank=True)
    handling_time = models.CharField(max_length=120, blank=True)
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    additional_item_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=CURRENCY_USD)
    duties_paid_by = models.CharField(max_length=20, choices=DUTIES_CHOICES, default=DUTIES_CUSTOMER)
    customs_notes = models.TextField(blank=True)
    return_policy = models.TextField(blank=True)
    restrictions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "international_shipping"
        ordering = ["sort_order", "destination_country", "service_name"]
        indexes = [
            models.Index(fields=["is_active", "destination_country_code"]),
            models.Index(fields=["sort_order", "destination_country"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.destination_country}"
