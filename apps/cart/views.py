from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.addresses.models import Address
from apps.core.responses import api_error, api_success
from apps.discounts.models import CouponCode
from apps.discounts.services.discount_service import validate_coupon_for_user
from apps.products.models import ProductVariant
from apps.shipping.models import ShippingMethod

from .models import Cart, CartVariantItem
from .serializers import CartSerializer
from .services.cart_service import calculate_cart_totals


def _positive_int(value, field_name: str, default=None):
    if value is None:
        if default is not None:
            value = default
        else:
            return None, api_error(f"{field_name} is required", {field_name: ["This field is required."]})
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, api_error(f"{field_name} must be an integer", {field_name: ["Enter a valid integer."]})
    if parsed < 1:
        return None, api_error(f"{field_name} must be at least 1", {field_name: ["Ensure this value is greater than or equal to 1."]})
    return parsed, None


def _cart_response(message: str, cart: Cart):
    return api_success(message, CartSerializer(cart).data)


class MyCartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return _cart_response("Cart fetched successfully", cart)


class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)

        variant_id, error = _positive_int(request.data.get("variantId"), "variantId")
        if error:
            return error

        quantity, error = _positive_int(request.data.get("quantity"), "quantity", default=1)
        if error:
            return error

        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return api_error("Variant not found", status_code=status.HTTP_404_NOT_FOUND)

        if not variant.is_active or not variant.product.is_active or not variant.product.is_published:
            return api_error("Variant is not available")

        existing_quantity = CartVariantItem.objects.filter(cart=cart, variant=variant).values_list("quantity", flat=True).first() or 0
        requested_quantity = existing_quantity + quantity
        if requested_quantity > variant.available_quantity:
            return api_error(
                "Insufficient stock",
                {"quantity": [f"Only {variant.available_quantity} item(s) available."]},
            )

        # Add or update cart item
        cart_item, created = CartVariantItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={"quantity": quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return _cart_response("Item added to cart successfully", cart)


class RemoveFromCartView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        cart, _ = Cart.objects.get_or_create(user=request.user)

        try:
            cart_item = CartVariantItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
        except CartVariantItem.DoesNotExist:
            return api_error("Cart item not found", status_code=status.HTTP_404_NOT_FOUND)

        return _cart_response("Item removed from cart", cart)

    def patch(self, request, item_id):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        quantity, error = _positive_int(request.data.get("quantity"), "quantity", default=1)
        if error:
            return error

        try:
            cart_item = CartVariantItem.objects.select_related("variant").get(id=item_id, cart=cart)
        except CartVariantItem.DoesNotExist:
            return api_error("Cart item not found", status_code=status.HTTP_404_NOT_FOUND)

        if quantity > cart_item.variant.available_quantity:
            return api_error(
                "Insufficient stock",
                {"quantity": [f"Only {cart_item.variant.available_quantity} item(s) available."]},
            )

        cart_item.quantity = quantity
        cart_item.save(update_fields=["quantity", "updated_at"])

        return _cart_response("Cart item updated successfully", cart)


class ClearCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.variant_items.all().delete()
        cart.bundle_items.all().delete()
        cart.applied_coupon = None
        cart.applied_discount_claim = None
        cart.save(update_fields=["applied_coupon", "applied_discount_claim", "updated_at"])
        return _cart_response("Cart cleared successfully", cart)


class SetShippingMethodView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        shipping_method_id, error = _positive_int(request.data.get("shipping_method_id"), "shipping_method_id")
        if error:
            return error

        shipping_method = ShippingMethod.objects.filter(id=shipping_method_id, is_active=True).first()
        if not shipping_method:
            return api_error("Shipping method not found", status_code=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.shipping_method = shipping_method
        cart.save(update_fields=["shipping_method", "updated_at"])
        return _cart_response("Shipping method updated successfully", cart)


class SetShippingAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        address_id, error = _positive_int(request.data.get("address_id"), "address_id")
        if error:
            return error

        address = Address.objects.filter(id=address_id, user=request.user, is_active=True).first()
        if not address:
            return api_error("Address not found", status_code=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.shipping_address = address
        cart.save(update_fields=["shipping_address", "updated_at"])
        return _cart_response("Shipping address updated successfully", cart)


class SetBillingAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        address_id, error = _positive_int(request.data.get("address_id"), "address_id")
        if error:
            return error

        address = Address.objects.filter(id=address_id, user=request.user, is_active=True).first()
        if not address:
            return api_error("Address not found", status_code=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.billing_address = address
        cart.save(update_fields=["billing_address", "updated_at"])
        return _cart_response("Billing address updated successfully", cart)


class MergeGuestCartView(APIView):
    """
    Merges guest cart items (from localStorage) with authenticated user's cart.
    Called when a user logs in.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Expected payload:
        {
            "guestItems": [
                {"variantId": 1, "quantity": 2},
                {"variantId": 3, "quantity": 1}
            ]
        }
        """
        cart, _ = Cart.objects.get_or_create(user=request.user)
        guest_items = request.data.get("guestItems", [])

        if not isinstance(guest_items, list):
            return api_error("guestItems must be a list", {"guestItems": ["Expected a list of cart items."]})

        merged_count = 0
        merged_variant_ids = []
        skipped_variant_ids = []
        capped_variant_ids = []
        for item in guest_items:
            if not isinstance(item, dict):
                continue
            variant_id, error = _positive_int(item.get("variantId"), "variantId")
            if error:
                continue
            quantity, error = _positive_int(item.get("quantity"), "quantity", default=1)
            if error:
                skipped_variant_ids.append(variant_id)
                continue

            try:
                variant = ProductVariant.objects.select_related("product").get(id=variant_id)
                if not variant.is_active or not variant.product.is_active:
                    skipped_variant_ids.append(variant_id)
                    continue

                existing_quantity = CartVariantItem.objects.filter(cart=cart, variant=variant).values_list("quantity", flat=True).first() or 0
                requested_quantity = existing_quantity + quantity
                available_quantity = variant.available_quantity
                if available_quantity < 1:
                    skipped_variant_ids.append(variant_id)
                    continue
                final_quantity = min(requested_quantity, available_quantity)
                if final_quantity < requested_quantity:
                    capped_variant_ids.append(variant_id)

                cart_item, created = CartVariantItem.objects.get_or_create(
                    cart=cart,
                    variant=variant,
                    defaults={"quantity": final_quantity}
                )

                if not created:
                    cart_item.quantity = max(cart_item.quantity, final_quantity)
                    cart_item.save(update_fields=["quantity", "updated_at"])

                merged_count += 1
                merged_variant_ids.append(variant_id)
            except ProductVariant.DoesNotExist:
                skipped_variant_ids.append(variant_id)
                continue

        data = CartSerializer(cart).data
        data["merged_count"] = merged_count
        data["merged_variant_ids"] = merged_variant_ids
        data["skipped_variant_ids"] = skipped_variant_ids
        data["capped_variant_ids"] = capped_variant_ids

        return api_success(
            f"Merged {merged_count} guest items into cart",
            data
        )


class ApplyCouponView(APIView):
    """
    Apply a coupon code to the user's cart.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").strip()
        
        if not code:
            return api_error("Coupon code is required", {"code": ["This field is required."]})
        
        # Get or create cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Find coupon
        coupon = CouponCode.objects.select_related("discount").filter(code=code).first()
        if not coupon:
            return api_error("Coupon code not found")
        if coupon.discount.first_order_only:
            return api_error("First-order discounts must be claimed with the email attached to your account")
        
        # Check if first-order discount is already applied
        if cart.applied_coupon and cart.applied_coupon.discount.first_order_only:
            return api_error("Cannot combine first-order discount with other promo codes")
        
        # Calculate subtotal to validate coupon
        totals = calculate_cart_totals(cart)
        subtotal = totals["subtotal"]
        
        # Validate coupon
        is_valid, reason = validate_coupon_for_user(coupon, request.user, subtotal)
        if not is_valid:
            return api_error(reason)
        
        # Apply coupon to cart
        cart.applied_coupon = coupon
        cart.applied_discount_claim = None
        cart.save(update_fields=["applied_coupon", "applied_discount_claim", "updated_at"])

        return _cart_response("Coupon applied successfully", cart)


class RemoveCouponView(APIView):
    """
    Remove the applied coupon from the user's cart.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        if not cart.applied_coupon:
            return api_error("No coupon applied to cart")
        
        # Remove coupon
        cart.applied_coupon = None
        cart.applied_discount_claim = None
        cart.save(update_fields=["applied_coupon", "applied_discount_claim", "updated_at"])

        return _cart_response("Coupon removed successfully", cart)
