from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.categories.models import Category
from apps.products.models import Product, ProductImage, ProductVariant

ASSETS_DIR = Path(settings.BASE_DIR) / "seed_assets" / "caps"

CAP_STYLES = (
    {"slug": "baseball", "name": "Baseball", "sort_order": 10},
    {"slug": "snapback", "name": "Snapback", "sort_order": 20},
    {"slug": "trucker", "name": "Trucker", "sort_order": 30},
    {"slug": "dad-cap", "name": "Dad Cap", "sort_order": 40},
    {"slug": "beanie", "name": "Beanie", "sort_order": 50},
    {"slug": "bucket-hat", "name": "Bucket Hat", "sort_order": 60},
)

CAP_PRODUCTS = (
    {
        "slug": "kofora-classic-baseball-cap",
        "name": "Kofora Classic Baseball Cap",
        "short_description": "Structured six-panel cap with a curved brim.",
        "full_description": (
            "A timeless six-panel baseball cap in breathable cotton twill. "
            "Structured crown, curved brim, and an adjustable strap for an easy everyday fit."
        ),
        "is_featured": True,
        "style": "baseball",
        "audiences": ("men", "women", "unisex"),
        "variants": (
            {
                "sku": "KOF-CAP-BB-BLK-OS",
                "color": "Black",
                "price": "27.99",
                "compare_at_price": "34.99",
                "cost_price": "11.50",
                "stock_quantity": 140,
                "color_mix": [{"name": "Black", "hex": "#111111", "quantity": 1}],
            },
            {
                "sku": "KOF-CAP-BB-NVY-OS",
                "color": "Navy",
                "price": "27.99",
                "compare_at_price": "34.99",
                "cost_price": "11.50",
                "stock_quantity": 90,
                "color_mix": [{"name": "Navy", "hex": "#1f2a44", "quantity": 1}],
            },
        ),
        "images": (
            ("baseball-black-1.jpg", "Black baseball cap resting on a chair"),
            ("baseball-black-2.jpg", "Man wearing the classic black baseball cap"),
        ),
    },
    {
        "slug": "kofora-fresh-snapback",
        "name": "Kofora Fresh Snapback",
        "short_description": "Flat-brim snapback with a clean minimal front.",
        "full_description": (
            "A flat-brim snapback with a high structured crown and adjustable snap closure. "
            "Minimal branding, maximum attitude - built to top off any street fit."
        ),
        "is_featured": True,
        "style": "snapback",
        "audiences": ("men", "women", "unisex"),
        "variants": (
            {
                "sku": "KOF-CAP-SB-WHT-OS",
                "color": "White",
                "price": "29.99",
                "compare_at_price": "36.99",
                "cost_price": "12.00",
                "stock_quantity": 110,
                "color_mix": [{"name": "White", "hex": "#f4f4f4", "quantity": 1}],
            },
            {
                "sku": "KOF-CAP-SB-SKY-OS",
                "color": "Sky Blue",
                "price": "29.99",
                "compare_at_price": "36.99",
                "cost_price": "12.00",
                "stock_quantity": 75,
                "color_mix": [{"name": "Sky Blue", "hex": "#8ecae6", "quantity": 1}],
            },
        ),
        "images": (
            ("snapback-white-1.jpg", "White snapback cap studio shot"),
            ("snapback-white-2.jpg", "Man adjusting a white snapback"),
            ("snapback-blue-1.jpg", "Sky blue snapback worn low"),
        ),
    },
    {
        "slug": "kofora-trucker-cap",
        "name": "Kofora Trucker Cap",
        "short_description": "Foam-front trucker with breathable mesh back.",
        "full_description": (
            "Classic trucker silhouette with a foam front panel and airy mesh back. "
            "Keeps you cool on long drives, trail days, and everything in between."
        ),
        "is_featured": False,
        "style": "trucker",
        "audiences": ("men", "unisex"),
        "variants": (
            {
                "sku": "KOF-CAP-TR-MNO-OS",
                "color": "Black/White",
                "price": "25.99",
                "compare_at_price": "31.99",
                "cost_price": "9.75",
                "stock_quantity": 130,
                "color_mix": [
                    {"name": "Black", "hex": "#111111", "quantity": 1},
                    {"name": "White", "hex": "#f4f4f4", "quantity": 1},
                ],
            },
            {
                "sku": "KOF-CAP-TR-WHT-OS",
                "color": "White",
                "price": "25.99",
                "compare_at_price": "31.99",
                "cost_price": "9.75",
                "stock_quantity": 95,
                "color_mix": [{"name": "White", "hex": "#f4f4f4", "quantity": 1}],
            },
        ),
        "images": (
            ("trucker-mono-1.jpg", "Black and white trucker cap on white background"),
            ("trucker-white-1.jpg", "All-white trucker cap product shot"),
        ),
    },
    {
        "slug": "kofora-everyday-dad-cap",
        "name": "Kofora Everyday Dad Cap",
        "short_description": "Soft unstructured cap in washed cotton.",
        "full_description": (
            "An unstructured low-profile dad cap in garment-washed cotton for a broken-in feel "
            "from day one. Adjustable buckle strap, endlessly easy to wear."
        ),
        "is_featured": False,
        "style": "dad-cap",
        "audiences": ("men", "women", "unisex"),
        "variants": (
            {
                "sku": "KOF-CAP-DC-WGR-OS",
                "color": "Washed Grey",
                "price": "23.99",
                "compare_at_price": "28.99",
                "cost_price": "8.50",
                "stock_quantity": 150,
                "color_mix": [{"name": "Washed Grey", "hex": "#9aa1ab", "quantity": 1}],
            },
            {
                "sku": "KOF-CAP-DC-MST-OS",
                "color": "Mustard",
                "price": "23.99",
                "compare_at_price": "28.99",
                "cost_price": "8.50",
                "stock_quantity": 85,
                "color_mix": [{"name": "Mustard", "hex": "#d9a520", "quantity": 1}],
            },
            {
                "sku": "KOF-CAP-DC-CRM-OS",
                "color": "Cream",
                "price": "23.99",
                "compare_at_price": "28.99",
                "cost_price": "8.50",
                "stock_quantity": 100,
                "color_mix": [{"name": "Cream", "hex": "#f5f0dc", "quantity": 1}],
            },
        ),
        "images": (
            ("dadcap-washed-1.jpg", "Washed grey dad cap product shot"),
            ("dadcap-mustard-1.jpg", "Mustard dad cap on white background"),
            ("dadcap-cream-1.jpg", "Cream dad cap worn against a yellow wall"),
        ),
    },
    {
        "slug": "kofora-ribbed-beanie",
        "name": "Kofora Ribbed Beanie",
        "short_description": "Chunky ribbed knit beanie with fold-over cuff.",
        "full_description": (
            "A chunky ribbed-knit beanie with a fold-over cuff. Soft, warm, and stretchy - "
            "the cold-weather counterpart to your favorite Kofora socks."
        ),
        "is_featured": True,
        "style": "beanie",
        "audiences": ("men", "women", "kids", "unisex"),
        "variants": (
            {
                "sku": "KOF-CAP-BN-CHR-OS",
                "color": "Charcoal",
                "price": "21.99",
                "compare_at_price": "26.99",
                "cost_price": "7.25",
                "stock_quantity": 160,
                "color_mix": [{"name": "Charcoal", "hex": "#3f4245", "quantity": 1}],
            },
            {
                "sku": "KOF-CAP-BN-MST-OS",
                "color": "Mustard",
                "price": "21.99",
                "compare_at_price": "26.99",
                "cost_price": "7.25",
                "stock_quantity": 90,
                "color_mix": [{"name": "Mustard", "hex": "#d9a520", "quantity": 1}],
            },
            {
                "sku": "KOF-CAP-BN-RST-OS",
                "color": "Rust",
                "price": "21.99",
                "compare_at_price": "26.99",
                "cost_price": "7.25",
                "stock_quantity": 70,
                "color_mix": [{"name": "Rust", "hex": "#b7410e", "quantity": 1}],
            },
        ),
        "images": (
            ("beanie-charcoal-1.jpg", "Charcoal ribbed beanie product shot"),
            ("beanie-mustard-1.jpg", "Mustard ribbed beanie flat lay"),
            ("beanie-rust-1.jpg", "Man wearing a rust ribbed beanie"),
        ),
    },
    {
        "slug": "kofora-bucket-hat",
        "name": "Kofora Bucket Hat",
        "short_description": "Relaxed cotton bucket hat with wide brim.",
        "full_description": (
            "A relaxed-fit cotton bucket hat with a downward-sloping brim for sun coverage. "
            "Packs flat, springs back - made for festivals, beach days, and city summers."
        ),
        "is_featured": False,
        "style": "bucket-hat",
        "audiences": ("women", "men", "unisex"),
        "variants": (
            {
                "sku": "KOF-CAP-BH-SGE-OS",
                "color": "Sage",
                "price": "31.99",
                "compare_at_price": "38.99",
                "cost_price": "13.00",
                "stock_quantity": 80,
                "color_mix": [{"name": "Sage", "hex": "#9caf88", "quantity": 1}],
            },
            {
                "sku": "KOF-CAP-BH-TDY-OS",
                "color": "Tie-Dye",
                "price": "33.99",
                "compare_at_price": "39.99",
                "cost_price": "14.25",
                "stock_quantity": 55,
                "color_mix": [
                    {"name": "Blue", "hex": "#2563eb", "quantity": 1},
                    {"name": "Purple", "hex": "#9333ea", "quantity": 1},
                    {"name": "Pink", "hex": "#f9a8d4", "quantity": 1},
                ],
            },
        ),
        "images": (
            ("bucket-sage-1.jpg", "Sage bucket hat worn outdoors"),
            ("bucket-tiedye-1.jpg", "Tie-dye bucket hat lifestyle shot"),
        ),
    },
)


class Command(BaseCommand):
    help = "Seed the caps product family: taxonomy, products, variants, and images"

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

        caps_category, created = Category.objects.get_or_create(
            slug="caps",
            defaults={
                "name": "Caps",
                "taxonomy_group": Category.TAXONOMY_PRODUCT_FAMILY,
                "description": "Headwear built for every day",
                "is_active": True,
                "sort_order": 2,
                "seo_title": "Kofora Caps",
                "seo_description": "Premium caps, beanies, and bucket hats",
                **audit,
            },
        )
        if not caps_category.taxonomy_group:
            caps_category.taxonomy_group = Category.TAXONOMY_PRODUCT_FAMILY
            caps_category.save(update_fields=["taxonomy_group"])
        if not caps_category.image:
            hero = self._asset("caps-hero.jpg")
            with hero.open("rb") as fh:
                caps_category.image.save("caps-hero.jpg", File(fh), save=True)
        self.stdout.write(f"Category 'caps' {'created' if created else 'already present'}")

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

        styles = {}
        for style in CAP_STYLES:
            styles[style["slug"]], style_created = Category.objects.get_or_create(
                slug=style["slug"],
                defaults={
                    "parent": caps_category,
                    "name": style["name"],
                    "taxonomy_group": Category.TAXONOMY_STYLE,
                    "description": f"{style['name']} caps",
                    "is_active": True,
                    "sort_order": style["sort_order"],
                    "seo_title": f"{style['name']} Caps",
                    "seo_description": f"Kofora {style['name'].lower()} caps",
                    **audit,
                },
            )
            if style_created:
                self.stdout.write(f"  style '{style['slug']}' created")

        for spec in CAP_PRODUCTS:
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
                caps_category,
                styles[spec["style"]],
                *(audiences[a] for a in spec["audiences"]),
            )

            for variant_spec in spec["variants"]:
                ProductVariant.objects.get_or_create(
                    sku=variant_spec["sku"],
                    defaults={
                        "product": product,
                        "title": f"{variant_spec['color']} / One Size",
                        "size": "One Size",
                        "color": variant_spec["color"],
                        "color_mix": variant_spec["color_mix"],
                        "price": Decimal(variant_spec["price"]),
                        "compare_at_price": Decimal(variant_spec["compare_at_price"]),
                        "cost_price": Decimal(variant_spec["cost_price"]),
                        "stock_quantity": variant_spec["stock_quantity"],
                        "reserved_quantity": 0,
                        "low_stock_threshold": 10,
                        "is_active": True,
                        "weight_grams": 90,
                        **audit,
                    },
                )

            if not ProductImage.objects.filter(product=product).exists():
                for sort_order, (filename, alt_text) in enumerate(spec["images"], start=1):
                    asset = self._asset(filename)
                    with asset.open("rb") as fh:
                        ProductImage.objects.create(
                            product=product,
                            image=File(fh, name=f"caps/{filename}"),
                            alt_text=alt_text,
                            sort_order=sort_order,
                            is_active=True,
                            **audit,
                        )

            self.stdout.write(
                f"Product '{spec['slug']}' {'created' if product_created else 'already present'} "
                f"({product.variants.count()} variants, {product.images.count()} images)"
            )

        self.stdout.write(self.style.SUCCESS("Caps seed completed."))
