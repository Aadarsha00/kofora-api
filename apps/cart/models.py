from django.conf import settings
from django.db import models

from apps.addresses.models import Address
from apps.core.models import TimeStampedModel
from apps.discounts.models import CouponCode
from apps.products.models import Bundle, ProductVariant
from apps.shipping.models import ShippingMethod


class Cart(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    currency = models.CharField(max_length=3, default="USD")
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.SET_NULL, related_name="cart_shipping")
    billing_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.SET_NULL, related_name="cart_billing")
    shipping_method = models.ForeignKey(ShippingMethod, null=True, blank=True, on_delete=models.SET_NULL)
    applied_coupon = models.ForeignKey(CouponCode, null=True, blank=True, on_delete=models.SET_NULL)
    is_abandoned = models.BooleanField(default=False)
    abandoned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "carts"


class CartVariantItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="variant_items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "cart_variant_items"
        unique_together = (("cart", "variant"),)


class CartBundleItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="bundle_items")
    bundle = models.ForeignKey(Bundle, on_delete=models.PROTECT, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "cart_bundle_items"
        unique_together = (("cart", "bundle"),)
