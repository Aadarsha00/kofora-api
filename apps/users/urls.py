from django.urls import path

from .views import AdminCustomerDetailView, AdminCustomerListView, AdminCustomerStatusView, ChangePasswordView, MeView

urlpatterns = [
    path("customers/", AdminCustomerListView.as_view(), name="users-admin-customers"),
    path("customers/<int:pk>/", AdminCustomerDetailView.as_view(), name="users-admin-customer-detail"),
    path("customers/<int:pk>/status/", AdminCustomerStatusView.as_view(), name="users-admin-customer-status"),
    path("me/", MeView.as_view(), name="users-me"),
    path("me/password/", ChangePasswordView.as_view(), name="users-change-password"),
]
