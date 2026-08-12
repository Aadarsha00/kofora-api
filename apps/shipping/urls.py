from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InternationalShippingViewSet,
    ShippingMethodViewSet,
    ShippingZoneViewSet,
    UPSAddressValidationView,
    UPSRateView,
    UPSTrackView,
)

router = DefaultRouter()
router.register("zones", ShippingZoneViewSet, basename="shipping-zone")
router.register("methods", ShippingMethodViewSet, basename="shipping-method")
router.register("international", InternationalShippingViewSet, basename="international-shipping")

urlpatterns = router.urls + [
    path("ups/rates/", UPSRateView.as_view(), name="ups-rates"),
    path("ups/track/<str:tracking_number>/", UPSTrackView.as_view(), name="ups-track"),
    path("ups/validate-address/", UPSAddressValidationView.as_view(), name="ups-validate-address"),
]
