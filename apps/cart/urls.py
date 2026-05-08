from django.urls import path

from .views import (
    AddToCartView,
    ApplyCouponView,
    ClearCartView,
    MergeGuestCartView,
    MyCartView,
    RemoveCouponView,
    RemoveFromCartView,
    SetBillingAddressView,
    SetShippingAddressView,
    SetShippingMethodView,
)

urlpatterns = [
    path("me/", MyCartView.as_view(), name="cart-me"),
    path("items/", AddToCartView.as_view(), name="cart-add"),
    path("items/<int:item_id>/", RemoveFromCartView.as_view(), name="cart-remove"),
    path("clear/", ClearCartView.as_view(), name="cart-clear"),
    path("merge-guest/", MergeGuestCartView.as_view(), name="cart-merge-guest"),
    path("shipping-method/", SetShippingMethodView.as_view(), name="cart-shipping-method"),
    path("shipping-address/", SetShippingAddressView.as_view(), name="cart-shipping-address"),
    path("billing-address/", SetBillingAddressView.as_view(), name="cart-billing-address"),
    path("apply-coupon/", ApplyCouponView.as_view(), name="cart-apply-coupon"),
    path("remove-coupon/", RemoveCouponView.as_view(), name="cart-remove-coupon"),
]
