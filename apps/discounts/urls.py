from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CouponCodeViewSet, CouponValidateView, DiscountViewSet, FirstOrderDiscountApplyView, FirstOrderDiscountView

router = DefaultRouter()
# "coupons" must be registered before the catch-all "" discount route so that
# /discounts/coupons/ resolves to the coupon viewset rather than discount detail.
router.register("coupons", CouponCodeViewSet, basename="coupon")
router.register("", DiscountViewSet, basename="discount")

urlpatterns = [
	path("coupons/validate/", CouponValidateView.as_view(), name="coupon-validate"),
	path("first-order/", FirstOrderDiscountView.as_view(), name="first-order-discount"),
	path("first-order/apply/", FirstOrderDiscountApplyView.as_view(), name="first-order-discount-apply"),
] + router.urls
