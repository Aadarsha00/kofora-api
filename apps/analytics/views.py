from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_success

from .services.analytics_service import revenue_summary


class RevenueSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return api_success("Analytics summary fetched successfully", revenue_summary())
