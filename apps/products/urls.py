from rest_framework.routers import DefaultRouter

from .views import BundleViewSet, ProductViewSet

router = DefaultRouter()
router.register("", ProductViewSet, basename="product")
router.register("bundles", BundleViewSet, basename="bundle")

urlpatterns = router.urls
