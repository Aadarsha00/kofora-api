from decimal import Decimal

from django.db import migrations


DEFAULT_METHODS = (
    {
        "code": "standard-us",
        "name": "UPS Ground",
        "ups_service_code": "03",
        "base_rate": Decimal("6.99"),
        "free_shipping_threshold": Decimal("50.00"),
    },
    {
        "code": "ups-2nd-day-air",
        "name": "UPS 2nd Day Air",
        "ups_service_code": "02",
        "base_rate": Decimal("19.99"),
        "free_shipping_threshold": None,
    },
    {
        "code": "ups-next-day-air",
        "name": "UPS Next Day Air",
        "ups_service_code": "01",
        "base_rate": Decimal("29.99"),
        "free_shipping_threshold": None,
    },
)


def seed_default_ups_methods(apps, schema_editor):
    ShippingZone = apps.get_model("shipping", "ShippingZone")
    ShippingMethod = apps.get_model("shipping", "ShippingMethod")

    zone = ShippingZone.objects.filter(country_code="US", state_code="").first()
    if zone is None:
        zone = ShippingZone.objects.create(
            name="United States",
            country_code="US",
            state_code="",
            is_active=True,
        )
    elif not zone.is_active:
        zone.is_active = True
        zone.save(update_fields=["is_active", "updated_at"])

    for method in DEFAULT_METHODS:
        ShippingMethod.objects.update_or_create(
            code=method["code"],
            defaults={
                "zone": zone,
                "name": method["name"],
                "ups_service_code": method["ups_service_code"],
                "base_rate": method["base_rate"],
                "free_shipping_threshold": method["free_shipping_threshold"],
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("shipping", "0003_shippingmethod_ups_service_code"),
    ]

    operations = [
        migrations.RunPython(seed_default_ups_methods, migrations.RunPython.noop),
    ]
