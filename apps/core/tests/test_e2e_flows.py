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
        shipping_method = ShippingMethod.objects.create(
            zone=shipping_zone,
            name="Standard",
            code="standard-us",
            base_rate=Decimal("5.00"),
            is_active=True,
        )

        address = Address.objects.create(
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
            shipping_address=address,
            billing_address=address,
            shipping_method=shipping_method,
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
