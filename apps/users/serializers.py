from rest_framework import serializers

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
        )
        read_only_fields = ("id", "role", "is_email_verified", "created_at")
