from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdminStaff
from .models import SiteImage
from .serializers import SiteImageSerializer


class SiteImageViewSet(viewsets.ModelViewSet):
    queryset = SiteImage.objects.all()
    serializer_class = SiteImageSerializer
    permission_classes = [ReadOnlyOrAdminStaff]
    lookup_field = "key"
    # Small config table (one row per storefront slot) — return everything unpaginated.
    pagination_class = None
