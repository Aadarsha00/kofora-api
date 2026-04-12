from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.core.responses import api_error, api_success

from .serializers import OrderSerializer
from .services.order_service import create_order_from_cart


class CreateOrderFromCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return api_error("Cart not found")
        order = create_order_from_cart(cart, customer_notes=request.data.get("customer_notes", ""))
        return api_success("Order created successfully", OrderSerializer(order).data)
