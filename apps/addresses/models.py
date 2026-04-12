from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Address(TimeStampedModel):
    ADDRESS_TYPE_HOME = "home"
    ADDRESS_TYPE_WORK = "work"
    ADDRESS_TYPE_OTHER = "other"

    ADDRESS_TYPE_CHOICES = (
        (ADDRESS_TYPE_HOME, "Home"),
        (ADDRESS_TYPE_WORK, "Work"),
        (ADDRESS_TYPE_OTHER, "Other"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    company = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=2)
    state_province = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default=ADDRESS_TYPE_HOME)
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "addresses"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_default_shipping"]), models.Index(fields=["user", "is_default_billing"])]

    def __str__(self):
        return f"{self.full_name} - {self.address_line_1}"
