from django.core.management.base import BaseCommand
from django.db import transaction

from apps.categories.models import Category
from apps.products.models import Product


ROOT_CATEGORIES = [
    {"slug": "socks", "name": "Socks", "sort_order": 10, "taxonomy_group": Category.TAXONOMY_PRODUCT_FAMILY},
    {"slug": "women", "name": "Women", "sort_order": 20, "taxonomy_group": Category.TAXONOMY_AUDIENCE},
    {"slug": "men", "name": "Men", "sort_order": 30, "taxonomy_group": Category.TAXONOMY_AUDIENCE},
    {"slug": "kids", "name": "Kids", "sort_order": 40, "taxonomy_group": Category.TAXONOMY_AUDIENCE},
    {"slug": "unisex", "name": "Unisex", "sort_order": 50, "taxonomy_group": Category.TAXONOMY_AUDIENCE},
]

SOCK_HEIGHTS = [
    {"slug": "no-show", "name": "No Show", "sort_order": 10, "aliases": []},
    {"slug": "ankle", "name": "Ankle", "sort_order": 20, "aliases": ["ankel"]},
    {"slug": "quarter", "name": "Quarter", "sort_order": 30, "aliases": []},
    {"slug": "half-calf", "name": "Half Calf", "sort_order": 40, "aliases": []},
    {
        "slug": "calf",
        "name": "Calf",
        "sort_order": 50,
        "aliases": ["mid-calf", "crew", "crew-socks"],
    },
    {"slug": "knee-high", "name": "Knee High", "sort_order": 60, "aliases": ["over-the-calf"]},
]

COLLECTIONS = [
    {
        "slug": "casual",
        "name": "Casual",
        "sort_order": 110,
        "aliases": ["socks-casual", "socks-everyday", "caps-everyday", "caps-lifestyle", "caps-travel"],
    },
    {
        "slug": "sport",
        "name": "Sport",
        "sort_order": 120,
        "aliases": [
            "sports",
            "socks-athletic",
            "socks-running",
            "socks-performance",
            "caps-running",
            "caps-performance",
            "caps-outdoor",
        ],
    },
    {
        "slug": "compression",
        "name": "Compression",
        "sort_order": 130,
        "aliases": ["socks-compression"],
    },
    {"slug": "grippers", "name": "Grippers", "sort_order": 140, "aliases": []},
    {
        "slug": "dressy",
        "name": "Dressy",
        "sort_order": 150,
        "aliases": ["formal", "formals", "socks-dress"],
    },
    {
        "slug": "cozy",
        "name": "Cozy",
        "sort_order": 160,
        "aliases": ["socks-outdoor", "socks-merino-wool"],
    },
]


class Command(BaseCommand):
    help = "Create and normalize the category-backed sock taxonomy."

    def _ensure_root(self, slug, name, sort_order, taxonomy_group):
        category, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "taxonomy_group": taxonomy_group,
                "is_active": True,
                "sort_order": sort_order,
            },
        )

        changed = False
        updates = {
            "parent": None,
            "name": name,
            "taxonomy_group": taxonomy_group,
            "is_active": True,
            "sort_order": sort_order,
        }
        for field, value in updates.items():
            if getattr(category, field) != value:
                setattr(category, field, value)
                changed = True
        if changed:
            category.save()
        return category

    def _merge_alias(self, alias_slug, target):
        alias = Category.objects.filter(slug=alias_slug).exclude(pk=target.pk).first()
        if not alias:
            return 0

        moved = 0
        for product in alias.products.all():
            product.categories.add(target)
            product.categories.remove(alias)
            moved += 1

        alias.is_active = False
        alias.save()
        return moved

    def _ensure_sock_child(self, parent, slug, name, sort_order, aliases, taxonomy_group):
        category = Category.objects.filter(slug=slug).first()
        renamed_from = None

        if category is None:
            alias = Category.objects.filter(slug__in=aliases).first()
            if alias:
                category = alias
                renamed_from = alias.slug
                category.slug = slug
            else:
                category = Category(slug=slug)

        changed = category.pk is None or renamed_from is not None or category.slug != slug
        updates = {
            "parent": parent,
            "name": name,
            "taxonomy_group": taxonomy_group,
            "is_active": True,
            "sort_order": sort_order,
        }
        for field, value in updates.items():
            if getattr(category, field) != value:
                setattr(category, field, value)
                changed = True
        if changed:
            category.save()

        moved = 0
        for alias_slug in aliases:
            if alias_slug == renamed_from:
                continue
            moved += self._merge_alias(alias_slug, category)
        return category, moved

    @transaction.atomic
    def handle(self, *args, **options):
        roots = {
            item["slug"]: self._ensure_root(
                item["slug"],
                item["name"],
                item["sort_order"],
                item["taxonomy_group"],
            )
            for item in ROOT_CATEGORIES
        }
        socks = roots["socks"]

        sock_signal_ids = {socks.id}
        active_taxonomy_ids = set()
        moved_alias_products = 0
        for item in SOCK_HEIGHTS:
            category, moved = self._ensure_sock_child(
                socks,
                item["slug"],
                item["name"],
                item["sort_order"],
                item["aliases"],
                Category.TAXONOMY_HEIGHT,
            )
            sock_signal_ids.add(category.id)
            active_taxonomy_ids.add(category.id)
            moved_alias_products += moved

        for item in COLLECTIONS:
            category, moved = self._ensure_sock_child(
                socks,
                item["slug"],
                item["name"],
                item["sort_order"],
                item["aliases"],
                Category.TAXONOMY_PURPOSE,
            )
            sock_signal_ids.add(category.id)
            active_taxonomy_ids.add(category.id)
            moved_alias_products += moved

        obsolete_taxonomy = Category.objects.filter(
            taxonomy_group__in=[Category.TAXONOMY_HEIGHT, Category.TAXONOMY_PURPOSE],
            is_active=True,
        ).exclude(pk__in=active_taxonomy_ids)
        deactivated = obsolete_taxonomy.update(is_active=False)

        tagged_products = 0
        for product in Product.objects.filter(categories__id__in=sock_signal_ids).distinct():
            if not product.categories.filter(pk=socks.pk).exists():
                product.categories.add(socks)
                tagged_products += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Sock taxonomy synced. "
                f"Alias product links moved: {moved_alias_products}. "
                f"Options deactivated: {deactivated}. "
                f"Products tagged with socks: {tagged_products}."
            )
        )
