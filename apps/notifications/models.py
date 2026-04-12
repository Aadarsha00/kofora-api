from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class NotificationTemplate(TimeStampedModel):
    code = models.SlugField(max_length=80, unique=True)
    subject_template = models.CharField(max_length=255)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "notification_templates"


class NotificationLog(TimeStampedModel):
    TYPE_EMAIL = "email"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notification_type = models.CharField(max_length=20, default=TYPE_EMAIL)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="queued")
    error_message = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "notification_logs"
