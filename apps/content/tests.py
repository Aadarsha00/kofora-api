from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import HomepageTile


class HomepageTileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            username="homepage-admin",
            email="homepage-admin@example.com",
            password="test-password",
            role="admin",
        )

    def test_default_tiles_are_seeded_in_storefront_order(self):
        tiles = list(HomepageTile.objects.values_list("key", flat=True))
        self.assertEqual(tiles, ["women", "men", "kids"])

    def test_public_list_only_returns_active_tiles(self):
        HomepageTile.objects.create(
            key="hidden",
            title="Hidden",
            href="/collections/hidden",
            sort_order=5,
            is_active=False,
        )

        response = self.client.get("/api/v1/homepage-tiles/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [tile["key"] for tile in response.data],
            ["women", "men", "kids"],
        )

    def test_admin_can_create_update_list_and_delete_tiles(self):
        self.client.force_authenticate(self.admin)

        create_response = self.client.post(
            "/api/v1/homepage-tiles/",
            {
                "title": "Summer Edit",
                "href": "/collections/women?purpose=casual",
                "sort_order": 15,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        tile_id = create_response.data["id"]
        self.assertEqual(create_response.data["key"], "summer-edit")

        update_response = self.client.patch(
            f"/api/v1/homepage-tiles/{tile_id}/",
            {"title": "Summer Collection", "is_active": False},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["title"], "Summer Collection")
        self.assertFalse(update_response.data["is_active"])

        list_response = self.client.get("/api/v1/homepage-tiles/")
        self.assertIn(tile_id, [tile["id"] for tile in list_response.data])

        delete_response = self.client.delete(f"/api/v1/homepage-tiles/{tile_id}/")
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(HomepageTile.objects.filter(id=tile_id).exists())

    def test_anonymous_users_cannot_create_tiles(self):
        response = self.client.post(
            "/api/v1/homepage-tiles/",
            {"title": "Blocked", "href": "/collections/blocked"},
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))

    def test_destination_requires_a_storefront_path_or_web_url(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/v1/homepage-tiles/",
            {"title": "Invalid", "href": "collections/women"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("href", response.data["errors"])
