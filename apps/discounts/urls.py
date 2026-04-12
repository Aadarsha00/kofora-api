from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CouponCodeViewSet, CouponValidateView, DiscountViewSet

router = DefaultRouter()
router.register("", DiscountViewSet, basename="discount")
router.register("coupons", CouponCodeViewSet, basename="coupon")

urlpatterns = [
	path("coupons/validate/", CouponValidateView.as_view(), name="coupon-validate"),
] + router.urls
