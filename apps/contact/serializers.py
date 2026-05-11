from rest_framework import serializers

from .models import ContactSubmission


class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "order_number",
            "topic",
            "message",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "status", "created_at")
