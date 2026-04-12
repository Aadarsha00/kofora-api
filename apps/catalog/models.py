from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import Product


class ProductCollection(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.CharField(max_length=255, blank=True)
    products = models.ManyToManyField(Product, related_name="collections", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "product_collections"
