from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.addresses.models import Address
from apps.cart.models import Cart, CartVariantItem
from apps.categories.models import Category
from apps.discounts.models import CouponCode, Discount
from apps.orders.models import Order
from apps.payments.models import PaymentTransaction
from apps.products.models import Product, ProductVariant
from apps.shipping.models import ShippingMethod, ShippingZone

User = get_user_model()


class E2EAuthFlowTests(APITestCase):
    @patch("apps.authentication.services.auth_services.send_email_task.delay")
    def test_register_and_login_returns_jwt_tokens(self, _mock_email):
        register_payload = {
            "email": "customer1@example.com",
            "username": "customer1",
            "password": "StrongPass123!",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "1234567890",
        }
        register_res = self.client.post("/api/v1/auth/register/", register_payload, format="json")
        self.assertEqual(register_res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(register_res.data["success"])

        login_payload = {"email": "customer1@example.com", "password": "StrongPass123!"}
        login_res = self.client.post("/api/v1/auth/login/", login_payload, format="json")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_res.data)
        self.assertIn("refresh", login_res.data)
        self.assertEqual(login_res.data["user"]["email"], "customer1@example.com")
        self.assertEqual(login_res.data["user"]["role"], "customer")


class E2ECheckoutLifecycleTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            username="buyer",
            password="StrongPass123!",
            role="customer",
        )
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name="Crew Socks", slug="crew-socks")
        self.product = Product.objects.create(
            name="Kofora Premium Crew",
            slug="kofora-premium-crew",
            base_currency="USD",
            is_active=True,
            is_published=True,
        )
        self.product.categories.add(self.category)
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="KOF-CRW-BLK-M",
            size="M",
            color="Black",
            price=Decimal("19.99"),
            stock_quantity=50,
            reserved_quantity=0,
            is_active=True,
        )

        shipping_zone = ShippingZone.objects.create(name="US", country_code="US")
        self.shipping_method = ShippingMethod.objects.create(
            zone=shipping_zone,
            name="Standard",
            code="standard-us",
            base_rate=Decimal("5.00"),
            is_active=True,
        )

        self.address = Address.objects.create(
            user=self.user,
            full_name="Jane Buyer",
            phone="5551231234",
            country="US",
            state_province="CA",
            city="San Francisco",
            postal_code="94105",
            address_line_1="123 Market St",
            address_line_2="",
            is_default_shipping=True,
            is_default_billing=True,
        )

        self.cart = Cart.objects.create(
            user=self.user,
            currency="USD",
            shipping_address=self.address,
            billing_address=self.address,
            shipping_method=self.shipping_method,
        )
        CartVariantItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)

    @patch("apps.payments.views.verify_stripe_signature", return_value=True)
    def test_order_creation_and_payment_webhook_updates_lifecycle(self, _mock_sig):
        create_res = self.client.post("/api/v1/orders/create-from-cart/", {"customer_notes": "Leave at door"}, format="json")
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        self.assertTrue(create_res.data["success"])

        order_id = create_res.data["data"]["id"]
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.fulfillment_status, Order.STATUS_AWAITING_PAYMENT)
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.customer_notes, "Leave at door")
        self.assertEqual(order.subtotal, Decimal("39.98"))
        self.assertEqual(order.discount_amount, Decimal("0.00"))
        self.assertEqual(order.shipping_amount, Decimal("5.00"))
        self.assertEqual(order.tax_amount, Decimal("3.60"))
        self.assertEqual(order.grand_total, Decimal("48.58"))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.address_snapshots.count(), 2)

        PaymentTransaction.objects.create(
            order=order,
            provider=PaymentTransaction.PROVIDER_STRIPE,
            provider_payment_id="pi_test_123",
            amount=order.grand_total,
            currency=order.currency,
            status=PaymentTransaction.STATUS_PENDING,
        )

        webhook_payload = {
            "id": "evt_test_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123",
                }
            },
        }
        webhook_res = self.client.post(
            "/api/v1/payments/webhooks/stripe/",
            webhook_payload,
            format="json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=test",
        )
        self.assertEqual(webhook_res.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.assertEqual(order.payment_status, "paid")
        self.assertEqual(order.fulfillment_status, Order.STATUS_PROCESSING)

    def test_order_creation_uses_coupon_adjusted_cart_totals(self):
        discount = Discount.objects.create(
            name="CHECKOUT10",
            discount_type=Discount.TYPE_PERCENT,
            percentage=Decimal("10.00"),
            is_active=True,
        )
        coupon = CouponCode.objects.create(discount=discount, code="CHECKOUT10", is_active=True)
        self.cart.applied_coupon = coupon
        self.cart.save(update_fields=["applied_coupon", "updated_at"])

        create_res = self.client.post("/api/v1/orders/create-from-cart/", {"customer_notes": "Coupon order"}, format="json")
        self.assertEqual(create_res.status_code, status.HTTP_200_OK)
        self.assertTrue(create_res.data["success"])

        order = Order.objects.get(id=create_res.data["data"]["id"])
        self.assertEqual(order.subtotal, Decimal("39.98"))
        self.assertEqual(order.discount_amount, Decimal("4.00"))
        self.assertEqual(order.shipping_amount, Decimal("5.00"))
        self.assertEqual(order.tax_amount, Decimal("3.28"))
        self.assertEqual(order.grand_total, Decimal("44.26"))
        self.assertEqual(order.fulfillment_status, Order.STATUS_AWAITING_PAYMENT)
        self.assertEqual(order.items.first().line_total, Decimal("39.98"))

    def test_cart_endpoints_match_frontend_contract(self):
        self.cart.shipping_address = None
        self.cart.billing_address = None
        self.cart.shipping_method = None
        self.cart.save(update_fields=["shipping_address", "billing_address", "shipping_method", "updated_at"])

        shipping_res = self.client.post(
            "/api/v1/cart/shipping-method/",
            {"shipping_method_id": self.shipping_method.id},
            format="json",
        )
        self.assertEqual(shipping_res.status_code, status.HTTP_200_OK)
        self.assertTrue(shipping_res.data["success"])
        self.assertEqual(shipping_res.data["data"]["shipping_method"], self.shipping_method.id)

        shipping_address_res = self.client.post(
            "/api/v1/cart/shipping-address/",
            {"address_id": self.address.id},
            format="json",
        )
        self.assertEqual(shipping_address_res.status_code, status.HTTP_200_OK)
        self.assertEqual(shipping_address_res.data["data"]["shipping_address"], self.address.id)

        billing_address_res = self.client.post(
            "/api/v1/cart/billing-address/",
            {"address_id": self.address.id},
            format="json",
        )
        self.assertEqual(billing_address_res.status_code, status.HTTP_200_OK)
        self.assertEqual(billing_address_res.data["data"]["billing_address"], self.address.id)

        clear_res = self.client.post("/api/v1/cart/clear/", {}, format="json")
        self.assertEqual(clear_res.status_code, status.HTTP_200_OK)
        self.assertTrue(clear_res.data["success"])
        self.assertEqual(clear_res.data["data"]["variant_items"], [])
        self.assertEqual(CartVariantItem.objects.filter(cart=self.cart).count(), 0)

    def test_guest_cart_merge_preserves_login_local_storage_flow(self):
        CartVariantItem.objects.filter(cart=self.cart).delete()
        second_variant = ProductVariant.objects.create(
            product=self.product,
            sku="KOF-CRW-BLK-L",
            size="L",
            color="Black",
            price=Decimal("21.99"),
            stock_quantity=10,
            reserved_quantity=0,
            is_active=True,
        )

        merge_res = self.client.post(
            "/api/v1/cart/merge-guest/",
            {
                "guestItems": [
                    {"variantId": self.variant.id, "quantity": 2},
                    {"variantId": second_variant.id, "quantity": 1},
                ]
            },
            format="json",
        )
        self.assertEqual(merge_res.status_code, status.HTTP_200_OK)
        self.assertTrue(merge_res.data["success"])
        self.assertEqual(set(merge_res.data["data"]["merged_variant_ids"]), {self.variant.id, second_variant.id})
        self.assertEqual(merge_res.data["data"]["skipped_variant_ids"], [])
        self.assertEqual(merge_res.data["data"]["capped_variant_ids"], [])
        self.assertEqual(len(merge_res.data["data"]["variant_items"]), 2)
        self.assertEqual(
            CartVariantItem.objects.get(cart=self.cart, variant=self.variant).quantity,
            2,
        )
        self.assertEqual(
            CartVariantItem.objects.get(cart=self.cart, variant=second_variant).quantity,
            1,
        )

        second_merge_res = self.client.post(
            "/api/v1/cart/merge-guest/",
            {"guestItems": [{"variantId": self.variant.id, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(second_merge_res.status_code, status.HTTP_200_OK)
        self.assertEqual(second_merge_res.data["data"]["merged_variant_ids"], [self.variant.id])
        self.assertEqual(
            CartVariantItem.objects.get(cart=self.cart, variant=self.variant).quantity,
            3,
        )

    def test_guest_cart_merge_caps_quantity_to_available_stock(self):
        CartVariantItem.objects.filter(cart=self.cart).delete()
        self.variant.stock_quantity = 18
        self.variant.reserved_quantity = 0
        self.variant.save(update_fields=["stock_quantity", "reserved_quantity", "updated_at"])
        CartVariantItem.objects.create(cart=self.cart, variant=self.variant, quantity=1)

        merge_res = self.client.post(
            "/api/v1/cart/merge-guest/",
            {"guestItems": [{"variantId": self.variant.id, "quantity": 18}]},
            format="json",
        )

        self.assertEqual(merge_res.status_code, status.HTTP_200_OK)
        self.assertTrue(merge_res.data["success"])
        self.assertEqual(merge_res.data["data"]["merged_variant_ids"], [self.variant.id])
        self.assertEqual(merge_res.data["data"]["skipped_variant_ids"], [])
        self.assertEqual(merge_res.data["data"]["capped_variant_ids"], [self.variant.id])
        self.assertEqual(
            CartVariantItem.objects.get(cart=self.cart, variant=self.variant).quantity,
            18,
        )

    def test_guest_cart_merge_accepts_existing_active_variant_when_product_is_unpublished(self):
        CartVariantItem.objects.filter(cart=self.cart).delete()
        self.product.is_published = False
        self.product.save(update_fields=["is_published", "updated_at"])

        merge_res = self.client.post(
            "/api/v1/cart/merge-guest/",
            {"guestItems": [{"variantId": self.variant.id, "quantity": 1}]},
            format="json",
        )

        self.assertEqual(merge_res.status_code, status.HTTP_200_OK)
        self.assertTrue(merge_res.data["success"])
        self.assertEqual(merge_res.data["data"]["merged_variant_ids"], [self.variant.id])
        self.assertEqual(merge_res.data["data"]["skipped_variant_ids"], [])
        self.assertEqual(merge_res.data["data"]["capped_variant_ids"], [])
        self.assertEqual(
            CartVariantItem.objects.get(cart=self.cart, variant=self.variant).quantity,
            1,
        )


class E2EDiscountValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="discount-user@example.com",
            username="discount-user",
            password="StrongPass123!",
            role="customer",
        )
        self.client.force_authenticate(user=self.user)

        self.discount = Discount.objects.create(
            name="SAVE10",
            discount_type=Discount.TYPE_PERCENT,
            percentage=Decimal("10.00"),
            minimum_order_amount=Decimal("100.00"),
            is_active=True,
        )
        self.coupon = CouponCode.objects.create(discount=self.discount, code="SAVE10", is_active=True)

    def test_coupon_validation_returns_reason_for_failure_and_success(self):
        low_subtotal_res = self.client.post(
            "/api/v1/discounts/coupons/validate/",
            {"code": "SAVE10", "subtotal": "40.00"},
            format="json",
        )
        self.assertEqual(low_subtotal_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(low_subtotal_res.data["success"])
        self.assertIn("Minimum order amount", low_subtotal_res.data["message"])

        valid_subtotal_res = self.client.post(
            "/api/v1/discounts/coupons/validate/",
            {"code": "SAVE10", "subtotal": "150.00"},
            format="json",
        )
        self.assertEqual(valid_subtotal_res.status_code, status.HTTP_200_OK)
        self.assertTrue(valid_subtotal_res.data["success"])
        self.assertEqual(Decimal(str(valid_subtotal_res.data["data"]["discount_amount"])), Decimal("15.00"))

    def test_first_order_discount_requires_matching_server_claim(self):
        first_order_discount = Discount.objects.filter(first_order_only=True).first()
        if not first_order_discount:
            first_order_discount = Discount.objects.create(
                name="FIRST20",
                discount_type=Discount.TYPE_PERCENT,
                percentage=Decimal("20.00"),
                minimum_order_amount=Decimal("0.00"),
                first_order_only=True,
                is_active=True,
            )
        CouponCode.objects.get_or_create(
            code="FIRST20",
            defaults={"discount": first_order_discount, "is_active": True},
        )

        manual_res = self.client.post("/api/v1/cart/apply-coupon/", {"code": "FIRST20"}, format="json")
        self.assertEqual(manual_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("must be claimed", manual_res.data["message"])

        mismatch_claim_res = self.client.post(
            "/api/v1/discounts/first-order/",
            {"email": "other-discount-user@example.com"},
            format="json",
        )
        self.assertEqual(mismatch_claim_res.status_code, status.HTTP_200_OK)
        mismatch_apply_res = self.client.post(
            "/api/v1/discounts/first-order/apply/",
            {"claim_token": mismatch_claim_res.data["data"]["claim_token"]},
            format="json",
        )
        self.assertEqual(mismatch_apply_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("must match", mismatch_apply_res.data["message"])

        claim_res = self.client.post(
            "/api/v1/discounts/first-order/",
            {"email": self.user.email},
            format="json",
        )
        self.assertEqual(claim_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(claim_res.data["data"]["discount_amount"])), Decimal("20.00"))

        apply_res = self.client.post(
            "/api/v1/discounts/first-order/apply/",
            {"claim_token": claim_res.data["data"]["claim_token"]},
            format="json",
        )
        self.assertEqual(apply_res.status_code, status.HTTP_200_OK)
        self.assertEqual(apply_res.data["data"]["applied_coupon"], "FIRST20")
        self.assertIsNotNone(apply_res.data["data"]["applied_discount_claim"])
