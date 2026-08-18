from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import CouponCode, Discount, DiscountRule


class DiscountRuleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = DiscountRule
        fields = (
            "id",
            "discount",
            "product",
            "product_name",
            "bundle",
            "subscription_plan",
            "category",
            "category_name",
            "role",
        )

    def validate(self, attrs):
        """A rule that names nothing would silently widen the discount to the
        whole catalogue, which is the opposite of what an admin adding a rule
        intends."""
        targets = [
            attrs.get("product") or getattr(self.instance, "product", None),
            attrs.get("bundle") or getattr(self.instance, "bundle", None),
            attrs.get("category") or getattr(self.instance, "category", None),
            attrs.get("subscription_plan") or getattr(self.instance, "subscription_plan", None),
        ]
        if not any(targets):
            raise serializers.ValidationError(
                {"product": "Pick a product, category, bundle or subscription plan for this rule."}
            )
        return attrs


class DiscountSerializer(serializers.ModelSerializer):
    rules = DiscountRuleSerializer(many=True, read_only=True)

    class Meta:
        model = Discount
        fields = "__all__"

    def validate(self, attrs):
        """Run the model's own consistency checks on the API path too.

        DRF does not call Model.clean(), so without this an admin could POST a
        bogo discount with no buy quantity and only find out when a cart
        silently failed to discount.
        """
        merged = {**{field: getattr(self.instance, field, None) for field in (
            "discount_type",
            "flat_amount",
            "percentage",
            "buy_quantity",
            "get_quantity",
            "reward_percentage",
            "max_applications",
            "starts_at",
            "expires_at",
        )}, **attrs} if self.instance else attrs

        candidate = Discount(**{key: value for key, value in merged.items() if key in {
            "discount_type",
            "flat_amount",
            "percentage",
            "buy_quantity",
            "get_quantity",
            "reward_percentage",
            "max_applications",
            "starts_at",
            "expires_at",
        }})
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)

        return attrs


class PublicOfferSerializer(serializers.ModelSerializer):
    """Storefront-safe view of an auto-applied offer, for badges and banners."""

    eligible_product_ids = serializers.SerializerMethodField()
    eligible_category_ids = serializers.SerializerMethodField()
    reward_product_ids = serializers.SerializerMethodField()
    reward_category_ids = serializers.SerializerMethodField()

    class Meta:
        model = Discount
        fields = (
            "id",
            "name",
            "discount_type",
            "buy_quantity",
            "get_quantity",
            "reward_percentage",
            "max_applications",
            "minimum_order_amount",
            "is_stackable",
            "starts_at",
            "expires_at",
            "eligible_product_ids",
            "eligible_category_ids",
            "reward_product_ids",
            "reward_category_ids",
        )

    def _ids(self, obj, role, attribute):
        return [
            getattr(rule, attribute)
            for rule in obj.rules.all()
            if rule.role == role and getattr(rule, attribute)
        ]

    def get_eligible_product_ids(self, obj):
        return self._ids(obj, DiscountRule.ROLE_ELIGIBLE, "product_id")

    def get_eligible_category_ids(self, obj):
        return self._ids(obj, DiscountRule.ROLE_ELIGIBLE, "category_id")

    def get_reward_product_ids(self, obj):
        return self._ids(obj, DiscountRule.ROLE_REWARD, "product_id")

    def get_reward_category_ids(self, obj):
        return self._ids(obj, DiscountRule.ROLE_REWARD, "category_id")


class CouponCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponCode
        fields = "__all__"
