from django.contrib import admin

from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "country", "city", "is_default_shipping", "is_default_billing", "is_active")
    list_filter = ("country", "is_default_shipping", "is_default_billing", "is_active")
    search_fields = ("user__email", "full_name", "phone", "postal_code")
