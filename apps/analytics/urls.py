from django.urls import path

from .views import AdminDashboardView, RevenueSummaryView

urlpatterns = [
    path("revenue-summary/", RevenueSummaryView.as_view(), name="analytics-revenue-summary"),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="analytics-admin-dashboard"),
]
