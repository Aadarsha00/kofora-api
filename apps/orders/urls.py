from django.urls import path

from .views import CreateOrderFromCartView, MyOrderDetailView, MyOrdersView

urlpatterns = [
    path("create-from-cart/", CreateOrderFromCartView.as_view(), name="orders-create-from-cart"),
    path("me/", MyOrdersView.as_view(), name="orders-me"),
    path("me/<int:order_id>/", MyOrderDetailView.as_view(), name="orders-me-detail"),
]
