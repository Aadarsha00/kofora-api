from rest_framework.routers import DefaultRouter

from .views import SiteImageViewSet

router = DefaultRouter()
router.register("", SiteImageViewSet, basename="site-image")

urlpatterns = router.urls
