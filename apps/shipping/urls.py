from rest_framework.routers import DefaultRouter

from .views import ShippingMethodViewSet, ShippingZoneViewSet

router = DefaultRouter()
router.register("zones", ShippingZoneViewSet, basename="shipping-zone")
router.register("methods", ShippingMethodViewSet, basename="shipping-method")

urlpatterns = router.urls
