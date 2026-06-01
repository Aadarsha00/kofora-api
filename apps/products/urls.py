from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
	BundleViewSet,
	ProductImageDetailView,
	ProductImageUploadView,
	ProductVariantLookupView,
	ProductVariantViewSet,
	ProductViewSet,
)

router = DefaultRouter()
router.register("bundles", BundleViewSet, basename="bundle")
router.register("variants", ProductVariantViewSet, basename="product-variant")
router.register("", ProductViewSet, basename="product")

urlpatterns = [
	path("variants/lookup/", ProductVariantLookupView.as_view(), name="products-variant-lookup"),
	path("images/upload/", ProductImageUploadView.as_view(), name="products-image-upload"),
	path("images/<int:pk>/", ProductImageDetailView.as_view(), name="products-image-detail"),
] + router.urls
