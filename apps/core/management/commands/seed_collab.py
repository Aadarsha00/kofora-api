from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.content.models import Collab
from apps.products.models import Product

CAPS_ASSETS = Path(settings.BASE_DIR) / "seed_assets" / "caps"
SOCKS_ASSETS = Path(settings.BASE_DIR) / "seed_assets" / "socks"

# Slugs seeded by seed_socks / seed_caps. Missing ones are skipped so the
# command still works on a partially seeded database.
COLLAB_PRODUCT_SLUGS = (
    "kofora-classic-baseball-cap",
    "kofora-fresh-snapback",
    "kofora-trucker-cap",
    "kofora-everyday-dad-cap",
    "kofora-ribbed-beanie",
    "kofora-bucket-hat",
    "kofora-everyday-no-show-sock",
    "kofora-ribbed-crew-sock",
    "kofora-compression-knee-high-sock",
)

COLLAB = {
    "slug": "marvel",
    "name": "Kofora x Marvel",
    "partner_name": "Marvel",
    "tagline": "Suit up from the socks up. A limited run of hero-worthy comfort.",
    "description": (
        "Nine styles built for everyday heroics. Same cushioned footbed, same "
        "seamless toe, same lifetime comfort guarantee - now in a limited "
        "partner colourway you can only get while the drop lasts."
    ),
    "accent_color": "#B91C1C",
    "text_color": "#FFFFFF",
    "cta_label": "Shop the collection",
    "sort_order": 10,
}


class Command(BaseCommand):
    help = "Seed a demo partner collab (homepage strip + landing page) with products and artwork"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip banner/hero artwork; the strip then renders as a flat accent panel.",
        )

    def _asset(self, directory: Path, filename: str) -> Path:
        path = directory / filename
        if not path.exists():
            raise CommandError(f"Seed asset missing: {path}")
        return path

    @transaction.atomic
    def handle(self, *args, **options):
        collab, created = Collab.objects.get_or_create(
            slug=COLLAB["slug"],
            defaults={key: value for key, value in COLLAB.items() if key != "slug"},
        )

        if not created:
            for key, value in COLLAB.items():
                if key != "slug":
                    setattr(collab, key, value)

        collab.is_active = True
        collab.show_on_homepage = True
        # Open-ended run so the demo never silently expires.
        collab.starts_at = None
        collab.ends_at = None

        if not options["no_images"]:
            # Only attach artwork when the record has none, so re-running the
            # command never clobbers an image an admin uploaded.
            if not collab.banner_image:
                banner = self._asset(CAPS_ASSETS, "caps-hero.jpg")
                with banner.open("rb") as handle:
                    collab.banner_image.save(f"collab-{collab.slug}-banner.jpg", File(handle), save=False)

            if not collab.hero_image:
                hero = self._asset(SOCKS_ASSETS, "socks-hero.webp")
                with hero.open("rb") as handle:
                    collab.hero_image.save(f"collab-{collab.slug}-hero.webp", File(handle), save=False)

        collab.save()

        products = list(Product.objects.filter(slug__in=COLLAB_PRODUCT_SLUGS))
        missing = set(COLLAB_PRODUCT_SLUGS) - {product.slug for product in products}
        collab.products.set(products)

        self.stdout.write(
            f"Collab '{collab.slug}' {'created' if created else 'updated'} "
            f"({len(products)} products, live={collab.is_live})"
        )
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped products not in the database: "
                    + ", ".join(sorted(missing))
                    + " - run seed_socks / seed_caps first."
                )
            )
        self.stdout.write(self.style.SUCCESS("Collab seed completed."))
