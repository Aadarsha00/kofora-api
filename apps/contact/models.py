from django.db import models

from apps.core.models import TimeStampedModel


class ContactSubmission(TimeStampedModel):
    TOPIC_ORDER = "order"
    TOPIC_RETURNS = "returns"
    TOPIC_SIZING = "sizing"
    TOPIC_PRODUCT = "product"
    TOPIC_GENERAL = "general"

    TOPIC_CHOICES = (
        (TOPIC_ORDER, "Order help"),
        (TOPIC_RETURNS, "Returns and exchanges"),
        (TOPIC_SIZING, "Sizing help"),
        (TOPIC_PRODUCT, "Product question"),
        (TOPIC_GENERAL, "General question"),
    )

    STATUS_NEW = "new"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"

    STATUS_CHOICES = (
        (STATUS_NEW, "New"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_RESOLVED, "Resolved"),
    )

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    order_number = models.CharField(max_length=64, blank=True)
    topic = models.CharField(max_length=24, choices=TOPIC_CHOICES, default=TOPIC_GENERAL)
    message = models.TextField()
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_NEW)

    class Meta:
        db_table = "contact_submissions"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.email} - {self.get_topic_display()}"
