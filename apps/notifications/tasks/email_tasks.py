from celery import shared_task
from django.core.mail import send_mail

from apps.notifications.models import NotificationLog


@shared_task
def send_email_task(subject: str, body: str, recipient: str):
    log = NotificationLog.objects.create(recipient=recipient, subject=subject, status="queued")
    try:
        send_mail(subject, body, None, [recipient], fail_silently=False)
        log.status = "sent"
        log.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)[:255]
        log.save(update_fields=["status", "error_message", "updated_at"])
