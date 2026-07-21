from rest_framework.routers import DefaultRouter

from .views import HomepageTileViewSet

router = DefaultRouter()
router.register("", HomepageTileViewSet, basename="homepage-tile")

urlpatterns = router.urls
