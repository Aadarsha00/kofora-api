from django.urls import path

from .views import CreateOrderFromCartView

urlpatterns = [
    path("create-from-cart/", CreateOrderFromCartView.as_view(), name="orders-create-from-cart"),
]