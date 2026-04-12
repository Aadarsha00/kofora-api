from django.contrib import admin

from .models import CustomerSubscription, SubscriptionEvent, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "price", "currency", "interval_unit", "is_active")
    list_filter = ("currency", "interval_unit", "is_active")
    search_fields = ("name", "slug", "stripe_price_id")


@admin.register(CustomerSubscription)
class CustomerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "plan", "status", "start_date", "renewal_date")
    list_filter = ("status", "plan")
    search_fields = ("customer__email", "stripe_subscription_id")


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    list_display = ("id", "subscription", "event_type", "source", "created_at")
    list_filter = ("event_type", "source")
