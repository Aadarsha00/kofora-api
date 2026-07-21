# Kofora — Socks + Caps navigation taxonomy seed (idempotent, safe to re-run).
#
# USAGE ON THE VPS: copy this ENTIRE file and paste it into your SSH terminal.
# Paths follow deployment/HOSTINGER_VPS_SETUP.md — adjust the two paths below
# if your layout differs.
#
# What it does:
#   * Ensures the root categories: Socks, Caps (product_family) and
#     Men, Women, Kids, Unisex (audience).
#   * Socks children — Height and shared Collection options,
#     and Best Sellers / New Arrivals / Multi Packs (plain nav nodes).
#   * Caps children — By Style (style group),
#     and Best Sellers / New Arrivals / Seasonal (plain nav nodes).
#   * Renames/merges legacy slugs into the storefront Height and Collection
#     vocabulary, moving product links across
#     and deactivating the leftover alias rows. Nothing is deleted.
#
# "Shop All / Men / Women / Kids" rows in the mega menu are intentionally NOT
# created per family: "Shop All" is the family category itself, and audiences
# are the global men/women/kids roots (products are tagged family + audience).

source /var/www/kofora/venv/bin/activate && cd /var/www/kofora/backend && python manage.py shell <<'PY'
from django.db import transaction

from apps.categories.models import Category
from apps.users.models import User

FAMILY = Category.TAXONOMY_PRODUCT_FAMILY
AUDIENCE = Category.TAXONOMY_AUDIENCE
HEIGHT = Category.TAXONOMY_HEIGHT
PURPOSE = Category.TAXONOMY_PURPOSE
STYLE = Category.TAXONOMY_STYLE

# Each row: (slug, name, sort_order, taxonomy_group, legacy alias slugs to absorb)
ROOTS = [
    ("socks", "Socks", 10, FAMILY, ()),
    ("caps", "Caps", 20, FAMILY, ()),
    ("men", "Men", 30, AUDIENCE, ()),
    ("women", "Women", 40, AUDIENCE, ()),
    ("kids", "Kids", 50, AUDIENCE, ()),
    ("unisex", "Unisex", 60, AUDIENCE, ()),
]

SOCKS_CHILDREN = [
    # By Height
    ("no-show", "No Show", 110, HEIGHT, ()),
    ("ankle", "Ankle", 120, HEIGHT, ("ankel",)),
    ("quarter", "Quarter", 130, HEIGHT, ()),
    ("half-calf", "Half Calf", 140, HEIGHT, ()),
    ("calf", "Calf", 150, HEIGHT, ("mid-calf", "crew", "crew-socks")),
    ("knee-high", "Knee High", 160, HEIGHT, ("over-the-calf",)),
    # By Collection
    ("casual", "Casual", 210, PURPOSE, ("socks-casual", "socks-everyday", "caps-everyday", "caps-lifestyle", "caps-travel")),
    ("sport", "Sport", 220, PURPOSE, ("sports", "socks-athletic", "socks-running", "socks-performance", "caps-running", "caps-performance", "caps-outdoor")),
    ("compression", "Compression", 230, PURPOSE, ("socks-compression",)),
    ("grippers", "Grippers", 240, PURPOSE, ()),
    ("dressy", "Dressy", 250, PURPOSE, ("formal", "formals", "socks-dress")),
    ("cozy", "Cozy", 260, PURPOSE, ("socks-outdoor", "socks-merino-wool")),
    # Merchandising nav nodes
    ("socks-best-sellers", "Best Sellers", 910, "", ()),
    ("socks-new-arrivals", "New Arrivals", 920, "", ()),
    ("socks-multi-packs", "Multi Packs", 930, "", ()),
]

CAPS_CHILDREN = [
    # By Style
    ("baseball", "Baseball Caps", 110, STYLE, ()),
    ("dad-cap", "Dad Caps", 120, STYLE, ()),
    ("trucker", "Trucker Caps", 130, STYLE, ()),
    ("snapback", "Snapbacks", 140, STYLE, ()),
    ("five-panel", "Five Panel", 150, STYLE, ()),
    ("bucket-hat", "Bucket Hats", 160, STYLE, ()),
    ("visors", "Visors", 170, STYLE, ()),
    ("performance-caps", "Performance Caps", 180, STYLE, ()),
    # Not in the new nav spec, but kept: seeded beanie products reference it.
    ("beanie", "Beanies", 190, STYLE, ()),
    # Merchandising nav nodes
    ("caps-best-sellers", "Best Sellers", 910, "", ()),
    ("caps-new-arrivals", "New Arrivals", 920, "", ()),
    ("caps-seasonal", "Seasonal", 930, "", ()),
]

admin_user = User.objects.filter(role=User.ROLE_ADMIN).order_by("id").first()
stats = {"created": 0, "renamed": 0, "updated": 0, "moved_product_links": 0, "merged_aliases": 0, "deactivated": 0}


def default_seo_title(name, parent, group):
    if parent is not None and group in (HEIGHT, PURPOSE) and parent.name.lower() not in name.lower():
        return f"{name} {parent.name}"
    return name


def ensure(slug, name, sort_order, group, aliases=(), parent=None):
    category = Category.objects.filter(slug=slug).first()
    renamed_from = None

    if category is None:
        category = Category.objects.filter(slug__in=list(aliases)).first()
        if category is not None:
            renamed_from = category.slug
            category.slug = slug
        else:
            category = Category(
                slug=slug,
                created_by=admin_user,
                seo_title=default_seo_title(name, parent, group),
                seo_description=f"Shop {name} at Kofora.",
            )

    is_new = category.pk is None
    changed = []
    for field, value in (
        ("parent", parent),
        ("name", name),
        ("taxonomy_group", group),
        ("is_active", True),
        ("sort_order", sort_order),
    ):
        if getattr(category, field) != value:
            setattr(category, field, value)
            changed.append(field)

    if is_new or renamed_from is not None or changed:
        if admin_user is not None:
            category.updated_by = admin_user
        category.save()
        if is_new:
            stats["created"] += 1
            print(f"  + created   {slug}  ({name})")
        elif renamed_from is not None:
            stats["renamed"] += 1
            print(f"  ~ renamed   {renamed_from} -> {slug}  ({name})")
        else:
            stats["updated"] += 1
            print(f"  ~ updated   {slug}: {', '.join(changed)}")

    for alias_slug in aliases:
        if alias_slug == renamed_from:
            continue
        alias = Category.objects.filter(slug=alias_slug).exclude(pk=category.pk).first()
        if alias is None:
            continue
        moved = 0
        for product in alias.products.all():
            product.categories.add(category)
            product.categories.remove(alias)
            moved += 1
        if moved or alias.is_active:
            if alias.is_active:
                alias.is_active = False
                if admin_user is not None:
                    alias.updated_by = admin_user
                alias.save()
            stats["moved_product_links"] += moved
            stats["merged_aliases"] += 1
            print(f"  - merged    {alias_slug} -> {slug}  ({moved} product link(s) moved, alias deactivated)")

    return category


with transaction.atomic():
    print("Roots (product families + audiences):")
    roots = {}
    for slug, name, sort_order, group, aliases in ROOTS:
        roots[slug] = ensure(slug, name, sort_order, group, aliases)

    print("Socks children (heights, collections, merchandising):")
    active_taxonomy_ids = set()
    for slug, name, sort_order, group, aliases in SOCKS_CHILDREN:
        category = ensure(slug, name, sort_order, group, aliases, parent=roots["socks"])
        if group in (HEIGHT, PURPOSE):
            active_taxonomy_ids.add(category.id)

    print("Caps children (styles, collections, merchandising):")
    for slug, name, sort_order, group, aliases in CAPS_CHILDREN:
        ensure(slug, name, sort_order, group, aliases, parent=roots["caps"])

    stats["deactivated"] = Category.objects.filter(
        taxonomy_group__in=(HEIGHT, PURPOSE), is_active=True
    ).exclude(pk__in=active_taxonomy_ids).update(is_active=False)

print()
print("Summary: " + ", ".join(f"{key}={value}" for key, value in stats.items()))
print()
print("Active category tree:")
for root in Category.objects.filter(parent__isnull=True, is_active=True).order_by("sort_order", "name"):
    print(f"  {root.name}  [{root.slug}]  <{root.taxonomy_group or 'nav'}>")
    for child in root.children.filter(is_active=True).order_by("sort_order", "name"):
        print(f"      {child.name}  [{child.slug}]  <{child.taxonomy_group or 'nav'}>")
PY
