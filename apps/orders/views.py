from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.core.permissions import IsAdminOrStaff
from apps.core.responses import api_error, api_success

from .models import Order
from .serializers import (
    AdminOrderDetailSerializer,
    AdminOrderListSerializer,
    AdminOrderStatusUpdateSerializer,
    OrderDetailSerializer,
    OrderSerializer,
)
from .services.order_service import create_order_from_cart, update_order_status


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


class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminOrStaff]
    queryset = (
        Order.objects.select_related("customer")
        .prefetch_related("items", "status_history", "address_snapshots")
        .all()
    )
    filterset_fields = ("fulfillment_status", "payment_status", "currency")
    search_fields = ("order_number", "customer__email", "customer__first_name", "customer__last_name")
    ordering_fields = ("created_at", "grand_total")
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return AdminOrderListSerializer
        return AdminOrderDetailSerializer

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = AdminOrderStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error("Invalid status update", serializer.errors)

        update_order_status(
            order,
            to_status=serializer.validated_data["fulfillment_status"],
            changed_by=request.user,
            note=serializer.validated_data.get("note", ""),
            staff_notes=serializer.validated_data.get("staff_notes"),
        )

        refreshed = (
            Order.objects.select_related("customer")
            .prefetch_related("items", "status_history", "address_snapshots")
            .get(pk=order.pk)
        )
        return api_success("Order status updated", AdminOrderDetailSerializer(refreshed).data)
