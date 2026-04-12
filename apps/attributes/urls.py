from rest_framework.routers import DefaultRouter

from .views import AttributeViewSet

router = DefaultRouter()
router.register("", AttributeViewSet, basename="attribute")

urlpatterns = router.urls
