from django.db import models

from apps.core.models import UserAuditModel
from apps.products.models import Product, ProductVariant


class Attribute(UserAuditModel):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "attributes"

    def __str__(self):
        return self.name


class AttributeOption(UserAuditModel):
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name="options")
    value = models.CharField(max_length=120)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "attribute_options"
        unique_together = (("attribute", "value"),)

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductAttributeValue(UserAuditModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="attribute_values")
    attribute = models.ForeignKey(Attribute, on_delete=models.PROTECT, related_name="product_values")
    option = models.ForeignKey(AttributeOption, on_delete=models.PROTECT, related_name="product_values")

    class Meta:
        db_table = "product_attribute_values"
        unique_together = (("product", "attribute", "option"),)


class VariantAttributeValue(UserAuditModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="attribute_values")
    attribute = models.ForeignKey(Attribute, on_delete=models.PROTECT, related_name="variant_values")
    option = models.ForeignKey(AttributeOption, on_delete=models.PROTECT, related_name="variant_values")

    class Meta:
        db_table = "variant_attribute_values"
        unique_together = (("variant", "attribute", "option"),)
