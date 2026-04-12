from django.db import models

from apps.core.models import UserAuditModel


class Category(UserAuditModel):
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["parent", "is_active"]), models.Index(fields=["slug"])]

    def __str__(self):
        return self.name
