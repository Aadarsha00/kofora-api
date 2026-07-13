from django.db import models

from apps.core.models import UserAuditModel


class Category(UserAuditModel):
    TAXONOMY_PRODUCT_FAMILY = "product_family"
    TAXONOMY_AUDIENCE = "audience"
    TAXONOMY_HEIGHT = "height"
    TAXONOMY_PURPOSE = "purpose"
    TAXONOMY_STYLE = "style"

    TAXONOMY_GROUP_CHOICES = (
        (TAXONOMY_PRODUCT_FAMILY, "Product family"),
        (TAXONOMY_AUDIENCE, "Audience"),
        (TAXONOMY_HEIGHT, "Height"),
        (TAXONOMY_PURPOSE, "Purpose"),
        (TAXONOMY_STYLE, "Style"),
    )

    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    taxonomy_group = models.CharField(max_length=32, choices=TAXONOMY_GROUP_CHOICES, blank=True, default="")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["parent", "is_active"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["taxonomy_group", "is_active"]),
        ]

    def __str__(self):
        return self.name
