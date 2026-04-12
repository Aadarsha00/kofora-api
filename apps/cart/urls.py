from django.urls import path

from .views import MyCartView

urlpatterns = [
    path("me/", MyCartView.as_view(), name="cart-me"),
]