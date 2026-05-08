from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BundleViewSet, ProductImageUploadView, ProductViewSet

router = DefaultRouter()
router.register("", ProductViewSet, basename="product")
router.register("bundles", BundleViewSet, basename="bundle")

urlpatterns = [
	path("images/upload/", ProductImageUploadView.as_view(), name="products-image-upload"),
] + router.urls
