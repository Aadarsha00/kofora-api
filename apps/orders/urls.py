from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AdminOrderViewSet, CreateOrderFromCartView, MyOrderDetailView, MyOrdersView

router = DefaultRouter()
router.register("admin", AdminOrderViewSet, basename="admin-order")

urlpatterns = [
    path("create-from-cart/", CreateOrderFromCartView.as_view(), name="orders-create-from-cart"),
    path("me/", MyOrdersView.as_view(), name="orders-me"),
    path("me/<int:order_id>/", MyOrderDetailView.as_view(), name="orders-me-detail"),
] + router.urls
