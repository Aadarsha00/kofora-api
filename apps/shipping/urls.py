from rest_framework.routers import DefaultRouter

from .views import InternationalShippingViewSet, ShippingMethodViewSet, ShippingZoneViewSet

router = DefaultRouter()
router.register("zones", ShippingZoneViewSet, basename="shipping-zone")
router.register("methods", ShippingMethodViewSet, basename="shipping-method")
router.register("international", InternationalShippingViewSet, basename="international-shipping")

urlpatterns = router.urls
