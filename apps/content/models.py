from django.db import models

from apps.core.models import UserAuditModel


class SiteImage(UserAuditModel):
    """An image for a fixed slot on the storefront (e.g. homepage banners).

    The frontend defines the known slot keys and their bundled fallbacks;
    a row here overrides the fallback for that slot.
    """

    key = models.SlugField(max_length=100, unique=True)
    image = models.ImageField(upload_to="site/")
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "site_images"
        ordering = ["key"]

    def __str__(self):
        return self.key
