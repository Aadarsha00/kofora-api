from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdminStaff, is_admin_or_staff_user
from .models import HomepageTile, SiteImage
from .serializers import HomepageTileSerializer, SiteImageSerializer


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
