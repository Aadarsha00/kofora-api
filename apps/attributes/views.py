from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdminStaff
from .models import Attribute
from .serializers import AttributeSerializer


class AttributeViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdminStaff]
    queryset = Attribute.objects.prefetch_related("options").all()
    serializer_class = AttributeSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "code")
