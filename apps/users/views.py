from django.db.models import Count, DecimalField, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrStaff
from apps.core.responses import api_error, api_success

from .models import User
from .serializers import AdminCustomerSerializer, AdminCustomerStatusSerializer, ChangePasswordSerializer, UserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return api_success("Profile fetched successfully", serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_error("Invalid profile data", serializer.errors)
        serializer.save()
        return api_success("Profile updated successfully", serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return api_error("Invalid password data", serializer.errors)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password", "updated_at"])
        return api_success("Password changed successfully")


class AdminCustomerQuerysetMixin:
    serializer_class = AdminCustomerSerializer
    permission_classes = [IsAdminOrStaff]

    def get_queryset(self):
        return (
            User.objects.filter(role=User.ROLE_CUSTOMER)
            .annotate(
                order_count=Count("orders", distinct=True),
                total_spend=Coalesce(
                    Sum("orders__grand_total", filter=Q(orders__payment_status="paid")),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                last_order_at=Max("orders__created_at"),
            )
            .order_by("-created_at")
        )


class AdminCustomerListView(AdminCustomerQuerysetMixin, generics.ListAPIView):
    search_fields = ("email", "username", "first_name", "last_name", "phone")
    filterset_fields = ("is_active", "is_email_verified", "marketing_opt_in")
    ordering_fields = ("created_at", "email", "order_count", "total_spend", "last_order_at")


class AdminCustomerDetailView(AdminCustomerQuerysetMixin, generics.RetrieveAPIView):
    pass


class AdminCustomerStatusView(AdminCustomerQuerysetMixin, APIView):
    def patch(self, request, pk):
        serializer = AdminCustomerStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error("Invalid customer status", serializer.errors)

        customer = self.get_queryset().filter(pk=pk).first()
        if not customer:
            return api_error("Customer not found", status_code=status.HTTP_404_NOT_FOUND)

        next_active = serializer.validated_data["is_active"]
        if customer.is_active != next_active:
            customer.is_active = next_active
            customer.save(update_fields=["is_active", "updated_at"])

        refreshed = self.get_queryset().get(pk=customer.pk)
        message = "Customer account reactivated" if next_active else "Customer account deactivated"
        return api_success(message, AdminCustomerSerializer(refreshed).data)
