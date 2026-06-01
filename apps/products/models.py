from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.categories.models import Category
from apps.core.models import UserAuditModel


class Product(UserAuditModel):
    CURRENCY_USD = "USD"
    CURRENCY_CAD = "CAD"

    CURRENCY_CHOICES = ((CURRENCY_USD, "USD"), (CURRENCY_CAD, "CAD"))

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    brand = models.CharField(max_length=120, default="Kofora")
    short_description = models.CharField(max_length=320, blank=True)
    full_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    base_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=CURRENCY_USD)
    is_published = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.CharField(max_length=500, blank=True)
    categories = models.ManyToManyField(Category, related_name="products", blank=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ProductImage(UserAuditModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    variant = models.ForeignKey(
        "ProductVariant",
        on_delete=models.SET_NULL,
        related_name="images",
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "product_images"
        ordering = ["sort_order", "id"]

    def clean(self):
        super().clean()
        if self.variant_id and self.product_id and self.variant.product_id != self.product_id:
            raise ValidationError({"variant": "Selected variant must belong to the same product as the image."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ProductVariant(UserAuditModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=80, unique=True)
    barcode = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=180, blank=True)
    size = models.CharField(max_length=80)
    color = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    image_override = models.ImageField(upload_to="products/variants/", null=True, blank=True)
    weight_grams = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "product_variants"
        indexes = [models.Index(fields=["product", "is_active"]), models.Index(fields=["size", "color"]), models.Index(fields=["price"])]

    def __str__(self):
        label = self.title or f"{self.color} / {self.size}"
        return f"{self.product.name} - {label} [{self.sku}]"

    @property
    def available_quantity(self):
        available = self.stock_quantity - self.reserved_quantity
        return available if available > 0 else 0


class Bundle(UserAuditModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bundles")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "bundles"


class BundleItem(UserAuditModel):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="bundle_items")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "bundle_items"
        unique_together = (("bundle", "variant"),)
