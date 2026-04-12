from django.contrib import admin

from .models import CustomerEvent, DailyMetric, EventType


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_funnel_step")
    search_fields = ("code", "name")


@admin.register(CustomerEvent)
class CustomerEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "user", "product", "variant", "session_id", "created_at")
    list_filter = ("event_type",)
    search_fields = ("session_id", "user__email")


@admin.register(DailyMetric)
class DailyMetricAdmin(admin.ModelAdmin):
    list_display = ("metric_date", "total_revenue", "order_count", "average_order_value", "repeat_customer_count")
