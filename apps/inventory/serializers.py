from rest_framework import serializers

from .models import InventoryAdjustment


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_title = serializers.CharField(source="variant.title", read_only=True)
    variant_size = serializers.CharField(source="variant.size", read_only=True)
    variant_color = serializers.CharField(source="variant.color", read_only=True)
    product_id = serializers.IntegerField(source="variant.product_id", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    adjusted_by_email = serializers.EmailField(source="adjusted_by.email", read_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = (
            "id",
            "variant",
            "variant_sku",
            "variant_title",
            "variant_size",
            "variant_color",
            "product_id",
            "product_name",
            "quantity_delta",
            "reason",
            "reference",
            "notes",
            "adjusted_by",
            "adjusted_by_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "adjusted_by", "created_at", "updated_at")

    def validate(self, attrs):
        variant = attrs.get("variant")
        quantity_delta = attrs.get("quantity_delta", 0)
        if variant and variant.stock_quantity + quantity_delta < variant.reserved_quantity:
            raise serializers.ValidationError(
                {
                    "quantity_delta": [
                        "Adjustment would make total stock lower than reserved stock."
                    ]
                }
            )
        return attrs
