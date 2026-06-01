from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrStaff
from apps.core.responses import api_success

from .services.analytics_service import dashboard_summary, revenue_summary


class RevenueSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return api_success("Analytics summary fetched successfully", revenue_summary())


class AdminDashboardView(APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        return api_success("Dashboard summary fetched successfully", dashboard_summary())
