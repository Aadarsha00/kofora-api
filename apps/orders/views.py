from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.core.responses import api_error, api_success

from .models import Order
from .serializers import OrderDetailSerializer, OrderSerializer
from .services.order_service import create_order_from_cart


class CreateOrderFromCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return api_error("Cart not found")
        try:
            order = create_order_from_cart(cart, customer_notes=request.data.get("customer_notes", ""))
        except ValueError as exc:
            return api_error(str(exc))
        return api_success("Order created successfully", OrderSerializer(order).data)


class MyOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(customer=request.user)
            .prefetch_related("items", "status_history")
            .order_by("-created_at")
        )
        return api_success("Orders fetched successfully", OrderDetailSerializer(orders, many=True).data)


class MyOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = (
            Order.objects.filter(id=order_id, customer=request.user)
            .prefetch_related("items", "status_history")
            .first()
        )
        if not order:
            return api_error("Order not found")
        return api_success("Order fetched successfully", OrderDetailSerializer(order).data)
