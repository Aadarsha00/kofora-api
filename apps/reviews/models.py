from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import Product


class Review(TimeStampedModel):
    MOD_PENDING = "pending"
    MOD_APPROVED = "approved"
    MOD_REJECTED = "rejected"

    MODERATION_CHOICES = (
        (MOD_PENDING, "Pending"),
        (MOD_APPROVED, "Approved"),
        (MOD_REJECTED, "Rejected"),
    )

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=180, blank=True)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    moderation_status = models.CharField(max_length=20, choices=MODERATION_CHOICES, default=MOD_PENDING)
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "reviews"
        unique_together = (("customer", "product"),)


class ReviewImage(TimeStampedModel):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="reviews/")
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "review_images"
