from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from apps.core.models import UserAuditModel


SITE_VIDEO_EXTENSIONS = ["mp4", "webm", "mov", "m4v", "ogg"]


class SiteImage(UserAuditModel):
    """Media for a fixed slot on the storefront (e.g. homepage banners).

    The frontend defines the known slot keys and their bundled fallbacks;
    a row here overrides the fallback for that slot. A slot holds a picture,
    a video, or both - a video takes precedence where the storefront supports
    one (the hero), and the picture stays as its poster/fallback frame.
    """

    key = models.SlugField(max_length=100, unique=True)
    image = models.ImageField(upload_to="site/", blank=True, null=True)
    video = models.FileField(
        upload_to="site/videos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=SITE_VIDEO_EXTENSIONS)],
        help_text="Optional background video for slots that support one.",
    )
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "site_images"
        ordering = ["key"]

    def __str__(self):
        return self.key


class HomepageTile(UserAuditModel):
    """An admin-managed category tile shown at the top of the homepage."""

    key = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=100)
    href = models.CharField(max_length=500)
    image = models.ImageField(upload_to="homepage-tiles/", blank=True, null=True)
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "homepage_tiles"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title


class Collab(UserAuditModel):
    """A limited-run partner collection (e.g. "Kofora x Marvel").

    Carries its own artwork and copy so the homepage strip and the collab
    landing page can be built entirely from admin data — no code change per
    partner. Products are attached through the M2M; a collab with no products
    still renders as a teaser.
    """

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    partner_name = models.CharField(max_length=150, blank=True)
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    logo = models.ImageField(upload_to="collabs/", null=True, blank=True)
    banner_image = models.ImageField(upload_to="collabs/", null=True, blank=True)
    hero_image = models.ImageField(upload_to="collabs/", null=True, blank=True)

    # Hex colours used for the homepage strip and the landing page hero.
    accent_color = models.CharField(max_length=7, default="#253E38")
    text_color = models.CharField(max_length=7, default="#FFFFFF")

    cta_label = models.CharField(max_length=80, default="Shop the collection")

    # Optional run window. Blank on either side means "open ended" on that side.
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    show_on_homepage = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    products = models.ManyToManyField(
        "products.Product", blank=True, related_name="collabs"
    )

    class Meta:
        db_table = "collabs"
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "show_on_homepage"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_live(self):
        """Active and inside its run window (if one is set)."""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True
