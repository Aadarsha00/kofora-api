from rest_framework.routers import DefaultRouter

from .views import CollabViewSet

router = DefaultRouter()
router.register("", CollabViewSet, basename="collab")

urlpatterns = router.urls
