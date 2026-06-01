from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import requests
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.responses import api_error, api_success
from apps.notifications.tasks.email_tasks import send_email_task
from apps.users.serializers import UserSerializer

from .models import GoogleOAuthAccount, PasswordResetToken
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


def _email_verified(value) -> bool:
    return value is True or str(value).lower() == "true"


def _unique_google_username(email: str) -> str:
    base = "".join(char for char in email.split("@")[0] if char.isalnum() or char == "_")[:24] or "google_user"
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix_text = str(suffix)
        candidate = f"{base[:150 - len(suffix_text) - 1]}_{suffix_text}"
        suffix += 1
    return candidate


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

    @transaction.atomic
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.GOOGLE_CLIENT_ID:
            return api_error("Google sign-in is not configured", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            token_response = requests.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": serializer.validated_data["id_token"]},
                timeout=8,
            )
        except requests.RequestException:
            return api_error("Unable to validate Google credential", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

        if token_response.status_code != status.HTTP_200_OK:
            return api_error("Invalid Google credential")

        try:
            google_profile = token_response.json()
        except ValueError:
            return api_error("Invalid Google credential")

        if google_profile.get("aud") != settings.GOOGLE_CLIENT_ID:
            errors = None
            if settings.DEBUG:
                errors = {
                    "expected_audience": settings.GOOGLE_CLIENT_ID,
                    "received_audience": google_profile.get("aud"),
                }
            return api_error("Google credential was issued for a different client", errors=errors)

        google_sub = google_profile.get("sub")
        email = google_profile.get("email")
        if not google_sub or not email or not _email_verified(google_profile.get("email_verified")):
            return api_error("Google account email is not verified")

        google_account = GoogleOAuthAccount.objects.select_related("user").filter(google_sub=google_sub).first()
        if google_account:
            user = google_account.user
            if google_account.email != email:
                google_account.email = email
                google_account.save(update_fields=["email", "updated_at"])
        else:
            user = User.objects.filter(email=email).first()
            if not user:
                user = User(
                    email=email,
                    username=_unique_google_username(email),
                    first_name=google_profile.get("given_name", ""),
                    last_name=google_profile.get("family_name", ""),
                    is_email_verified=True,
                )
                user.set_unusable_password()
                user.save()
            elif hasattr(user, "google_account"):
                return api_error(
                    "This email is already linked to another Google account",
                    status_code=status.HTTP_409_CONFLICT,
                )

            GoogleOAuthAccount.objects.create(user=user, google_sub=google_sub, email=email)

        update_fields = []
        if not user.is_email_verified:
            user.is_email_verified = True
            update_fields.append("is_email_verified")
        if not user.first_name and google_profile.get("given_name"):
            user.first_name = google_profile["given_name"]
            update_fields.append("first_name")
        if not user.last_name and google_profile.get("family_name"):
            user.last_name = google_profile["family_name"]
            update_fields.append("last_name")
        if update_fields:
            update_fields.append("updated_at")
            user.save(update_fields=update_fields)

        refresh = RefreshToken.for_user(user)
        return api_success(
            "Google login successful",
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
        )
