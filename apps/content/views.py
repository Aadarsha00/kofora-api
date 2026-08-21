from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdminStaff, is_admin_or_staff_user
from .models import Collab, HomepageTile, SiteImage
from .serializers import (
    CollabSerializer,
    CollabSummarySerializer,
    HomepageTileSerializer,
    SiteImageSerializer,
)


class SiteImageViewSet(viewsets.ModelViewSet):
    queryset = SiteImage.objects.all()
    serializer_class = SiteImageSerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    lookup_field = "key"
    # Small config table (one row per storefront slot) — return everything unpaginated.
    pagination_class = None


class HomepageTileViewSet(viewsets.ModelViewSet):
    queryset = HomepageTile.objects.all()
    serializer_class = HomepageTileSerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if not is_admin_or_staff_user(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CollabViewSet(viewsets.ModelViewSet):
    queryset = Collab.objects.all().prefetch_related("products__images", "products__variants")
    serializer_class = CollabSerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_admin_or_staff_user(self.request.user):
            return queryset

        # Shoppers only ever see collabs that are inside their run window.
        now = timezone.now()
        return queryset.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now)
        ).filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))

    def get_serializer_class(self):
        # The list endpoint feeds the homepage strip, which never needs the
        # nested products.
        if self.action == "list":
            return CollabSummarySerializer
        return CollabSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
