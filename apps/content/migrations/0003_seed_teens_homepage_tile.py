from django.db import migrations


def seed_teens_homepage_tile(apps, schema_editor):
    HomepageTile = apps.get_model("content", "HomepageTile")
    if HomepageTile.objects.filter(key="teens").exists():
        return
    HomepageTile.objects.create(
        key="teens",
        title="Teens",
        href="/collections/teens",
        sort_order=40,
        alt_text="Shop Teens",
    )


def remove_teens_homepage_tile(apps, schema_editor):
    HomepageTile = apps.get_model("content", "HomepageTile")
    HomepageTile.objects.filter(key="teens").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0002_homepagetile"),
    ]

    operations = [
        migrations.RunPython(
            seed_teens_homepage_tile,
            remove_teens_homepage_tile,
        ),
    ]
