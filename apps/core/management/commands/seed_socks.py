from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.categories.models import Category
from apps.products.models import Product, ProductImage, ProductVariant

ASSETS_DIR = Path(settings.BASE_DIR) / "seed_assets" / "socks"

# seed_data.py only creates a handful of sock subcategories - these three height
# and two purpose categories are specific to the products below, so this seed
# creates them itself (get_or_create) rather than assuming they already exist.
HEIGHT_CATEGORIES = {
    "no-show": "No Show",
    "crew-socks": "Crew",
    "knee-high": "Knee High",
}
PURPOSE_CATEGORIES = {
    "casual": "Casual",
    "compression": "Compression",
}

# Each product below has exactly one real product photo, so sizes (not colors)
# are the variant axis - listing invented colorways with no matching photo is
# the exact mismatch problem this seed replaces.
SIZE_VARIANTS = (
    {"label": "Small (6-8)", "suffix": "S", "stock": 60},
    {"label": "Medium (9-11)", "suffix": "M", "stock": 90},
    {"label": "Large (12-14)", "suffix": "L", "stock": 50},
)

SOCK_PRODUCTS = (
    {
        "slug": "kofora-everyday-no-show-sock",
        "name": "Kofora Everyday No-Show Sock",
        "short_description": "Low-cut sock that stays hidden below the shoe line.",
        "full_description": (
            "A breathable everyday no-show sock in soft charcoal marle. Cut low enough to "
            "disappear inside loafers and sneakers, with a silicone heel grip so it stays put."
        ),
        "is_featured": True,
        "style": "no-show",
        "purpose": "casual",
        "audiences": ("men", "women", "unisex"),
        "color": "Charcoal",
        "color_hex": "#3f4245",
        "price": "14.99",
        "compare_at_price": "18.99",
        "cost_price": "6.00",
        "weight_grams": 60,
        "sku_prefix": "KOF-SCK-NS-CHR",
        "image": ("no-show-charcoal-1.webp", "Charcoal no-show sock worn with a leather loafer"),
    },
    {
        "slug": "kofora-ribbed-crew-sock",
        "name": "Kofora Ribbed Crew Sock",
        "short_description": "Retro-striped crew sock with a ribbed knit.",
        "full_description": (
            "A crew-length sock in a heavyweight ribbed knit with a retro double stripe. "
            "Sits mid-calf for a throwback look that layers well with sandals or high-tops."
        ),
        "is_featured": True,
        "style": "crew-socks",
        "purpose": "casual",
        # Photo shows a slender, hairless leg with no male markers - women/unisex
        # only, not "men", since the audience tag should match what's shown.
        "audiences": ("women", "unisex"),
        "color": "Mustard Stripe",
        "color_hex": "#d9a520",
        "price": "16.99",
        "compare_at_price": "21.99",
        "cost_price": "7.25",
        "weight_grams": 70,
        "sku_prefix": "KOF-SCK-CR-MST",
        "image": ("crew-mustard-stripe-1.webp", "Mustard and cream striped crew sock worn with sandals"),
    },
    {
        "slug": "kofora-compression-knee-high-sock",
        "name": "Kofora Compression Knee-High Sock",
        "short_description": "Graduated-compression sock for travel and long days on foot.",
        "full_description": (
            "A knee-high compression sock with graduated support through the calf. "
            "Built for travel days, long shifts on foot, and recovery after training."
        ),
        "is_featured": False,
        "style": "knee-high",
        "purpose": "compression",
        # Photo is unambiguously a male model (visible leg hair) - tagging this
        # "women" too would misrepresent what the product photo actually shows.
        "audiences": ("men",),
        "color": "White",
        "color_hex": "#f4f4f4",
        "price": "18.99",
        "compare_at_price": "24.99",
        "cost_price": "8.50",
        "weight_grams": 80,
        "sku_prefix": "KOF-SCK-KH-WHT",
        "image": ("knee-high-white-1.webp", "White graduated-compression knee-high sock"),
    },
)


class Command(BaseCommand):
    help = "Seed the socks product family: taxonomy, products, variants, and images"

    def _asset(self, filename: str) -> Path:
        path = ASSETS_DIR / filename
        if not path.exists():
            raise CommandError(f"Seed asset missing: {path}")
        return path

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        admin_user = User.objects.filter(role="admin").order_by("id").first()
        if admin_user is None:
            raise CommandError("No admin user found. Run `manage.py seed_data` first.")

        audit = {"created_by": admin_user, "updated_by": admin_user}

        socks_category = Category.objects.get(slug="socks")
        if not socks_category.image:
            hero = self._asset("socks-hero.webp")
            with hero.open("rb") as fh:
                socks_category.image.save("socks-hero.webp", File(fh), save=True)

        audiences = {}
        for slug, name in (("men", "Men"), ("women", "Women"), ("kids", "Kids"), ("unisex", "Unisex")):
            audiences[slug], _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "taxonomy_group": Category.TAXONOMY_AUDIENCE,
                    "is_active": True,
                    **audit,
                },
            )

        height_categories = {}
        for slug, name in HEIGHT_CATEGORIES.items():
            height_categories[slug], _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "parent": socks_category,
                    "name": name,
                    "taxonomy_group": Category.TAXONOMY_HEIGHT,
                    "is_active": True,
                    **audit,
                },
            )

        purpose_categories = {}
        for slug, name in PURPOSE_CATEGORIES.items():
            purpose_categories[slug], _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "parent": socks_category,
                    "name": name,
                    "taxonomy_group": Category.TAXONOMY_PURPOSE,
                    "is_active": True,
                    **audit,
                },
            )

        for spec in SOCK_PRODUCTS:
            style_category = height_categories[spec["style"]]
            purpose_category = purpose_categories[spec["purpose"]]

            product, product_created = Product.objects.get_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "brand": "Kofora",
                    "short_description": spec["short_description"],
                    "full_description": spec["full_description"],
                    "is_active": True,
                    "is_featured": spec["is_featured"],
                    "base_currency": Product.CURRENCY_USD,
                    "is_published": True,
                    "seo_title": spec["name"],
                    "seo_description": spec["short_description"],
                    **audit,
                },
            )
            product.categories.add(
                socks_category,
                style_category,
                purpose_category,
                *(audiences[a] for a in spec["audiences"]),
            )

            for size_spec in SIZE_VARIANTS:
                ProductVariant.objects.get_or_create(
                    sku=f"{spec['sku_prefix']}-{size_spec['suffix']}",
                    defaults={
                        "product": product,
                        "title": f"{spec['color']} / {size_spec['label']}",
                        "size": size_spec["label"],
                        "color": spec["color"],
                        "color_mix": [{"name": spec["color"], "hex": spec["color_hex"], "quantity": 1}],
                        "price": Decimal(spec["price"]),
                        "compare_at_price": Decimal(spec["compare_at_price"]),
                        "cost_price": Decimal(spec["cost_price"]),
                        "stock_quantity": size_spec["stock"],
                        "reserved_quantity": 0,
                        "low_stock_threshold": 10,
                        "is_active": True,
                        "weight_grams": spec["weight_grams"],
                        **audit,
                    },
                )

            if not ProductImage.objects.filter(product=product).exists():
                filename, alt_text = spec["image"]
                asset = self._asset(filename)
                with asset.open("rb") as fh:
                    ProductImage.objects.create(
                        product=product,
                        image=File(fh, name=f"socks/{filename}"),
                        alt_text=alt_text,
                        sort_order=1,
                        is_primary=True,
                        is_active=True,
                        **audit,
                    )

            self.stdout.write(
                f"Product '{spec['slug']}' {'created' if product_created else 'already present'} "
                f"({product.variants.count()} variants, {product.images.count()} images)"
            )

        self.stdout.write(self.style.SUCCESS("Socks seed completed."))
