import random
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.notifications.tasks.email_tasks import send_email_task

from ..models import EmailOTP, GoogleOAuthAccount, PasswordResetToken

User = get_user_model()


def generate_and_send_otp(user):
    code = f"{random.randint(100000, 999999)}"
    otp = EmailOTP.objects.create(
        user=user,
        email=user.email,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    send_email_task.delay(
        subject="Your Kofora OTP",
        body=f"Your verification code is {code}. It expires in 10 minutes.",
        recipient=user.email,
    )
    return otp


def verify_otp(email: str, code: str) -> bool:
    otp = EmailOTP.objects.filter(email=email, code=code, is_used=False).order_by("-created_at").first()
    if not otp or otp.is_expired():
        return False
    otp.is_used = True
    otp.save(update_fields=["is_used", "updated_at"])
    user = otp.user
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified", "updated_at"])
    return True


def create_password_reset_token(user):
    token = secrets.token_urlsafe(48)
    reset_token = PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    reset_link = f"{user.email} token: {token}"
    send_email_task.delay(
        subject="Kofora password reset",
        body=f"Use this reset token: {reset_link}",
        recipient=user.email,
    )
    return reset_token
