from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.products.models import Product


class CategoryAudienceAvailabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.women = Category.objects.create(
            name="Women",
            slug="women",
            taxonomy_group=Category.TAXONOMY_AUDIENCE,
        )
        self.men = Category.objects.create(
            name="Men",
            slug="men",
            taxonomy_group=Category.TAXONOMY_AUDIENCE,
        )
        self.socks = Category.objects.create(
            name="Socks",
            slug="socks",
            taxonomy_group=Category.TAXONOMY_PRODUCT_FAMILY,
        )
        self.caps = Category.objects.create(
            name="Caps",
            slug="caps",
            taxonomy_group=Category.TAXONOMY_PRODUCT_FAMILY,
        )
        self.casual = Category.objects.create(
            parent=self.socks,
            name="Casual",
            slug="casual",
            taxonomy_group=Category.TAXONOMY_PURPOSE,
        )
        self.dad_cap = Category.objects.create(
            parent=self.caps,
            name="Dad Caps",
            slug="dad-cap",
            taxonomy_group=Category.TAXONOMY_STYLE,
        )

    def test_categories_include_audiences_with_active_published_products(self):
        womens_socks = Product.objects.create(
            name="Women's Casual Socks",
            slug="womens-casual-socks",
            is_active=True,
            is_published=True,
        )
        womens_socks.categories.add(self.women, self.socks, self.casual)

        mens_cap = Product.objects.create(
            name="Men's Dad Cap",
            slug="mens-dad-cap",
            is_active=True,
            is_published=True,
        )
        mens_cap.categories.add(self.men, self.caps, self.dad_cap)

        response = self.client.get("/api/v1/categories/?page_size=100")

        self.assertEqual(response.status_code, 200)
        categories = response.data["results"]
        socks = next(category for category in categories if category["slug"] == "socks")
        caps = next(category for category in categories if category["slug"] == "caps")
        casual = next(child for child in socks["children"] if child["slug"] == "casual")
        dad_cap = next(child for child in caps["children"] if child["slug"] == "dad-cap")

        self.assertEqual(casual["available_audiences"], ["women"])
        self.assertEqual(dad_cap["available_audiences"], ["men"])

    def test_unpublished_products_do_not_make_categories_available(self):
        draft_cap = Product.objects.create(
            name="Draft Women's Dad Cap",
            slug="draft-womens-dad-cap",
            is_active=True,
            is_published=False,
        )
        draft_cap.categories.add(self.women, self.caps, self.dad_cap)

        response = self.client.get("/api/v1/categories/?page_size=100")

        self.assertEqual(response.status_code, 200)
        categories = response.data["results"]
        caps = next(category for category in categories if category["slug"] == "caps")
        dad_cap = next(child for child in caps["children"] if child["slug"] == "dad-cap")
        self.assertEqual(dad_cap["available_audiences"], [])


class StorefrontTaxonomySyncTests(TestCase):
    def test_sync_creates_exact_options_and_preserves_legacy_product_links(self):
        socks = Category.objects.create(
            name="Socks",
            slug="socks",
            taxonomy_group=Category.TAXONOMY_PRODUCT_FAMILY,
        )
        women = Category.objects.create(
            name="Women",
            slug="women",
            taxonomy_group=Category.TAXONOMY_AUDIENCE,
        )
        crew = Category.objects.create(
            parent=socks,
            name="Crew",
            slug="crew-socks",
            taxonomy_group=Category.TAXONOMY_HEIGHT,
        )
        athletic = Category.objects.create(
            parent=socks,
            name="Athletic",
            slug="socks-athletic",
            taxonomy_group=Category.TAXONOMY_PURPOSE,
        )
        product = Product.objects.create(
            name="Legacy Sport Socks",
            slug="legacy-sport-socks",
            is_active=True,
            is_published=True,
        )
        product.categories.add(socks, women, crew, athletic)

        call_command("sync_sock_taxonomy")

        active_heights = list(
            Category.objects.filter(taxonomy_group=Category.TAXONOMY_HEIGHT, is_active=True)
            .order_by("sort_order")
            .values_list("slug", flat=True)
        )
        active_collections = list(
            Category.objects.filter(taxonomy_group=Category.TAXONOMY_PURPOSE, is_active=True)
            .order_by("sort_order")
            .values_list("slug", flat=True)
        )
        product.refresh_from_db()

        self.assertEqual(
            active_heights,
            ["no-show", "ankle", "quarter", "half-calf", "calf", "knee-high"],
        )
        self.assertEqual(
            active_collections,
            ["casual", "sport", "compression", "grippers", "dressy", "cozy"],
        )
        self.assertTrue(product.categories.filter(slug="calf").exists())
        self.assertTrue(product.categories.filter(slug="sport").exists())
