from django.urls import path

from .views import RevenueSummaryView

urlpatterns = [
    path("revenue-summary/", RevenueSummaryView.as_view(), name="analytics-revenue-summary"),
]