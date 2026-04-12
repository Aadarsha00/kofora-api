from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class SearchQueryLog(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    query = models.CharField(max_length=255)
    category_slug = models.CharField(max_length=180, blank=True)
    size = models.CharField(max_length=80, blank=True)
    color = models.CharField(max_length=80, blank=True)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "search_query_logs"
