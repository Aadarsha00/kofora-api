from django.urls import path

from .views import (
    ForgotPasswordView,
    GoogleOAuthLoginView,
    LoginView,
    LogoutView,
    OTPRequestView,
    OTPVerifyView,
    RefreshView,
    RegisterView,
    ResetPasswordView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", RefreshView.as_view(), name="auth-token-refresh"),
    path("otp/send/", OTPRequestView.as_view(), name="auth-otp-send"),
    path("otp/verify/", OTPVerifyView.as_view(), name="auth-otp-verify"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("google/login/", GoogleOAuthLoginView.as_view(), name="auth-google-login"),
]