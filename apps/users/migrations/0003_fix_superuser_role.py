from django.db import migrations


def promote_superusers(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(is_superuser=True).exclude(role="admin").update(role="admin")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_user_managers"),
    ]

    operations = [
        migrations.RunPython(promote_superusers, noop),
    ]
