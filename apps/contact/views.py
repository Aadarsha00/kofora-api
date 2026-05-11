from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser

from .models import ContactSubmission
from .serializers import ContactSubmissionSerializer


class ContactSubmissionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ContactSubmissionSerializer
    queryset = ContactSubmission.objects.all()
    filterset_fields = ("topic", "status", "email")
    search_fields = ("first_name", "last_name", "email", "order_number", "message")
    ordering_fields = ("created_at", "topic", "status")

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAdminUser()]
