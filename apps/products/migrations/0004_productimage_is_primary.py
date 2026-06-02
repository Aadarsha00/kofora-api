# Generated manually for explicit product and variant primary images.

from django.db import migrations, models


def mark_existing_primary_images(apps, schema_editor):
    ProductImage = apps.get_model("products", "ProductImage")

    default_product_ids = (
        ProductImage.objects.filter(is_active=True, variant__isnull=True)
        .values_list("product_id", flat=True)
        .distinct()
    )

    for product_id in default_product_ids:
        first_image = (
            ProductImage.objects.filter(
                product_id=product_id,
                variant__isnull=True,
                is_active=True,
            )
            .order_by("sort_order", "id")
            .first()
        )
        if first_image:
            ProductImage.objects.filter(pk=first_image.pk).update(is_primary=True)

    color_groups = (
        ProductImage.objects.filter(is_active=True, variant__isnull=False)
        .values_list("product_id", "variant__color")
        .distinct()
    )

    for product_id, color in color_groups:
        first_image = (
            ProductImage.objects.filter(
                product_id=product_id,
                variant__color=color,
                is_active=True,
            )
            .order_by("sort_order", "id")
            .first()
        )
        if first_image:
            ProductImage.objects.filter(pk=first_image.pk).update(is_primary=True)


def clear_primary_images(apps, schema_editor):
    ProductImage = apps.get_model("products", "ProductImage")
    ProductImage.objects.update(is_primary=False)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_productimage_variant"),
    ]

    operations = [
        migrations.AddField(
            model_name="productimage",
            name="is_primary",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="productimage",
            index=models.Index(fields=["product", "variant", "is_primary"], name="product_ima_product_686890_idx"),
        ),
        migrations.AddIndex(
            model_name="productimage",
            index=models.Index(fields=["product", "variant", "sort_order"], name="product_ima_product_e5a523_idx"),
        ),
        migrations.RunPython(mark_existing_primary_images, clear_primary_images),
    ]
