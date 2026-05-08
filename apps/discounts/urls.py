from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CouponCodeViewSet, CouponValidateView, DiscountViewSet, FirstOrderDiscountApplyView, FirstOrderDiscountView

router = DefaultRouter()
router.register("", DiscountViewSet, basename="discount")
router.register("coupons", CouponCodeViewSet, basename="coupon")

urlpatterns = [
	path("coupons/validate/", CouponValidateView.as_view(), name="coupon-validate"),
	path("first-order/", FirstOrderDiscountView.as_view(), name="first-order-discount"),
	path("first-order/apply/", FirstOrderDiscountApplyView.as_view(), name="first-order-discount-apply"),
] + router.urls
