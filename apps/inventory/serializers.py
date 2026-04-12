from rest_framework import serializers

from .models import InventoryAdjustment


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryAdjustment
        fields = "__all__"
