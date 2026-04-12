from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Review.objects.select_related("customer", "product").prefetch_related("images")
    filterset_fields = ("product", "is_verified_purchase", "moderation_status", "is_published", "rating")

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)
