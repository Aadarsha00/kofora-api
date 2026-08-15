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

# seed_data.py only creates a handful of sock subcategories - these height and
# purpose categories are specific to the products below, so this seed creates
# them itself (get_or_create) rather than assuming they already exist. "calf"
# is the exception: seed_data.py already created it (for its own throwaway
# demo product, since removed), so this just adopts the existing category and
# finally gives it a real product.
HEIGHT_CATEGORIES = {
    "no-show": "No Show",
    "crew-socks": "Crew",
    "knee-high": "Knee High",
    "ankle": "Ankle",
    "quarter": "Quarter",
    "half-calf": "Half Calf",
    "calf": "Calf",
}
PURPOSE_CATEGORIES = {
    "casual": "Casual",
    "compression": "Compression",
    "sport": "Sport",
    "grippers": "Grippers",
    "dressy": "Dressy",
    "cozy": "Cozy",
}

# Each product below has exactly one real product photo, so sizes (not colors)
# are the variant axis - listing invented colorways with no matching photo is
# the exact mismatch problem this seed replaces.
SIZE_VARIANTS = (
    {"label": "Small (6-8)", "suffix": "S", "stock": 60},
    {"label": "Medium (9-11)", "suffix": "M", "stock": 90},
    {"label": "Large (12-14)", "suffix": "L", "stock": 50},
)

# Kids' shoe sizing is a different scale entirely - adult "Small (6-8)" would
# be actively misleading on a children's product.
KIDS_SIZE_VARIANTS = (
    {"label": "Small (Toddler 4-7)", "suffix": "S", "stock": 70},
    {"label": "Medium (Kids 8-12)", "suffix": "M", "stock": 100},
    {"label": "Large (Kids 13-3)", "suffix": "L", "stock": 60},
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
        "audiences": ("men", "women", "unisex"),
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
        "audiences": ("men", "women"),
        "color": "White",
        "color_hex": "#f4f4f4",
        "price": "18.99",
        "compare_at_price": "24.99",
        "cost_price": "8.50",
        "weight_grams": 80,
        "sku_prefix": "KOF-SCK-KH-WHT",
        "image": ("knee-high-white-1.webp", "White graduated-compression knee-high sock"),
    },
    {
        "slug": "kofora-sheer-ankle-sock",
        "name": "Kofora Sheer Ankle Sock",
        "short_description": "Lightweight ankle-length sock with a barely-there feel.",
        "full_description": (
            "A fine-knit ankle sock that sits just above the anklebone. Sheer enough to layer "
            "under trousers, substantial enough for daily wear."
        ),
        "is_featured": False,
        "style": "ankle",
        "purpose": "casual",
        "audiences": ("women", "unisex"),
        "color": "Navy",
        "color_hex": "#1a1f36",
        "price": "13.99",
        "compare_at_price": "17.99",
        "cost_price": "5.75",
        "weight_grams": 55,
        "sku_prefix": "KOF-SCK-AK-NVY",
        "image": ("ankle-navy-1.webp", "Navy ankle-length sock worn on crossed legs"),
    },
    {
        "slug": "kofora-active-quarter-sock",
        "name": "Kofora Active Quarter Sock",
        "short_description": "Ribbed quarter-length sock built for everyday movement.",
        "full_description": (
            "A cushioned quarter-length sock in a ribbed knit, cut just above the ankle bone. "
            "Breathable and durable enough for workouts, still clean enough for everyday wear."
        ),
        "is_featured": False,
        "style": "quarter",
        "purpose": "sport",
        "audiences": ("men", "women", "unisex"),
        "color": "White",
        "color_hex": "#f4f4f4",
        "price": "15.99",
        "compare_at_price": "19.99",
        "cost_price": "6.50",
        "weight_grams": 65,
        "sku_prefix": "KOF-SCK-QT-WHT",
        "image": ("quarter-white-1.webp", "White ribbed quarter-length sock being pulled on"),
    },
    {
        "slug": "kofora-pinstripe-half-calf-sock",
        "name": "Kofora Pinstripe Half-Calf Sock",
        "short_description": "Fine pinstripe dress sock in a mid-calf length.",
        "full_description": (
            "A fine-gauge pinstripe sock in a mid-calf length, made to disappear under tailored "
            "trousers. The dress-sock finish your good shoes deserve."
        ),
        "is_featured": False,
        "style": "half-calf",
        "purpose": "dressy",
        "audiences": ("men",),
        "color": "Brown",
        "color_hex": "#4a3728",
        "price": "17.99",
        "compare_at_price": "22.99",
        "cost_price": "7.50",
        "weight_grams": 70,
        "sku_prefix": "KOF-SCK-HC-BRN",
        "image": ("halfcalf-pinstripe-1.jpg", "Brown pinstripe half-calf dress sock worn with tailored pants"),
    },
    {
        "slug": "kofora-cozy-calf-sock",
        "name": "Kofora Cozy Calf Sock",
        "short_description": "Plush ribbed sock in a relaxed calf length.",
        "full_description": (
            "A soft, plush ribbed sock in a relaxed calf-length fit. Made for slow mornings, "
            "worn-in sneakers, and staying in just a little longer."
        ),
        "is_featured": False,
        "style": "calf",
        "purpose": "cozy",
        "audiences": ("men", "women", "unisex"),
        "color": "White",
        "color_hex": "#f4f4f4",
        "price": "16.99",
        "compare_at_price": "20.99",
        "cost_price": "6.75",
        "weight_grams": 75,
        "sku_prefix": "KOF-SCK-CZ-WHT",
        "image": ("cozy-calf-white-1.webp", "Plush white ribbed calf sock worn with a sneaker"),
    },
    {
        "slug": "kofora-kids-gripper-sock",
        "name": "Kofora Kids Gripper Sock",
        "short_description": "Knee-high gripper sock with non-slip soles, sized for kids.",
        "full_description": (
            "A colorful knee-high sock with grip dots on the sole to keep little feet steady on "
            "hardwood and tile. Soft, stretchy, and built for climbing on furniture they're not "
            "supposed to climb on."
        ),
        "is_featured": False,
        "style": "knee-high",
        "purpose": "grippers",
        "audiences": ("kids",),
        "color": "Chevron Multi",
        "color_hex": "#8b1e3f",
        "price": "12.99",
        "compare_at_price": "15.99",
        "cost_price": "5.25",
        "weight_grams": 50,
        "sku_prefix": "KOF-SCK-GR-MLT",
        "size_variants": KIDS_SIZE_VARIANTS,
        "image": ("kids-gripper-1.webp", "Child wearing colorful chevron-pattern knee-high gripper socks"),
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

            for size_spec in spec.get("size_variants", SIZE_VARIANTS):
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
