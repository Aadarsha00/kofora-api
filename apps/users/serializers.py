from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "phone",
            "is_email_verified",
            "marketing_opt_in",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "role", "is_email_verified", "created_at", "updated_at")


class AdminCustomerSerializer(serializers.ModelSerializer):
    order_count = serializers.IntegerField(read_only=True)
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    last_order_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "phone",
            "is_active",
            "is_email_verified",
            "marketing_opt_in",
            "order_count",
            "total_spend",
            "last_order_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminCustomerStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value
