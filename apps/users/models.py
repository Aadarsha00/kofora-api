from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models

from apps.core.models import TimeStampedModel


class UserManager(DjangoUserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.ROLE_ADMIN)
        return super().create_superuser(username=username, email=email, password=password, **extra_fields)


class User(AbstractUser, TimeStampedModel):
    ROLE_ADMIN = "admin"
    ROLE_STAFF = "staff"
    ROLE_CUSTOMER = "customer"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_STAFF, "Staff"),
        (ROLE_CUSTOMER, "Customer"),
    )

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone = models.CharField(max_length=30, blank=True)
    is_email_verified = models.BooleanField(default=False)
    marketing_opt_in = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    preferred_currency = models.CharField(max_length=3, default="USD")
    loyalty_points = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"Profile<{self.user_id}>"
