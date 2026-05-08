from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.responses import api_error, api_success
from apps.notifications.tasks.email_tasks import send_email_task

from .models import PasswordResetToken
from .serializers import (
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
)
from .services.auth_services import create_password_reset_token, generate_and_send_otp, verify_otp

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Send OTP asynchronously (don't wait for response)
        try:
            generate_and_send_otp(user)
        except Exception as e:
            # Log the error but don't fail the signup
            print(f"Error sending OTP: {e}")
        return api_success("Registration successful. OTP sent to email.", {"user_id": user.id}, status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return api_error("Refresh token is required", {"refresh": ["This field is required."]})
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return api_error("Invalid refresh token")
        return api_success("Logout successful")


class OTPRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email).first()
        if not user:
            return api_error("User not found", {"email": ["No account found with this email"]}, status.HTTP_404_NOT_FOUND)
        generate_and_send_otp(user)
        return api_success("OTP sent successfully")


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not verify_otp(serializer.validated_data["email"], serializer.validated_data["code"]):
            return api_error("Invalid or expired OTP")
        return api_success("OTP verified successfully")


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user:
            create_password_reset_token(user)
        return api_success("If your email exists, a reset token has been sent")


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = PasswordResetToken.objects.filter(
            token=serializer.validated_data["token"],
            is_used=False,
        ).first()
        if not reset_token or reset_token.expires_at <= timezone.now():
            return api_error("Invalid reset token")

        user = reset_token.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        reset_token.is_used = True
        reset_token.save(update_fields=["is_used", "updated_at"])
        return api_success("Password reset successful")


class GoogleOAuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Replace this stub with token exchange + Google userinfo validation.
        return api_success("Google OAuth flow endpoint is ready", {"received_code": serializer.validated_data["code"]})
