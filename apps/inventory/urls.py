from rest_framework.routers import DefaultRouter

from .views import InventoryAdjustmentViewSet

router = DefaultRouter()
router.register("adjustments", InventoryAdjustmentViewSet, basename="inventory-adjustments")

urlpatterns = router.urls
