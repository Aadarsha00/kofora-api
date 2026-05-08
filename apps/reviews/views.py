from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from apps.core.responses import api_success

from .models import Review
from .serializers import ReviewImageUploadSerializer, ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Review.objects.select_related("customer", "product").prefetch_related("images")
    filterset_fields = ("product", "is_verified_purchase", "moderation_status", "is_published", "rating")

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


class ReviewImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReviewImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_obj = serializer.save()
        return api_success(
            "Review image uploaded successfully",
            ReviewImageUploadSerializer(image_obj).data,
        )
