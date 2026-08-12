from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.addresses.models import Address
from apps.cart.models import Cart, CartVariantItem
from apps.cart.services.cart_service import calculate_cart_totals, resolve_shipping_amount
from apps.products.models import Product, ProductVariant
from apps.shipping.models import ShippingMethod, ShippingZone
from apps.shipping.services.ups_client import UPSError

User = get_user_model()

SHIPPING_SETTINGS = dict(
    UPS_SHIPPER_COUNTRY="US",
    UPS_DEFAULT_ITEM_WEIGHT_GRAMS=150,
    UPS_MIN_PACKAGE_WEIGHT_LBS="1",
    UPS_RATE_CACHE_SECONDS=3600,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**SHIPPING_SETTINGS)
class ResolveShippingAmountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="buyer@example.com", username="buyer", password="StrongPass123!"
        )
        self.zone = ShippingZone.objects.create(name="US", country_code="US")
        self.product = Product.objects.create(
            name="Crew Sock", slug="crew-sock", base_currency="USD", is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="CRW-1", size="M", color="Black",
            price=Decimal("19.99"), stock_quantity=50, weight_grams=200,
        )
        self.address = Address.objects.create(
            user=self.user, full_name="Jane Buyer", phone="5551231234",
            country="US", state_province="IL", city="Chicago", postal_code="60601",
            address_line_1="500 W Madison St",
        )

    def _cart(self, method=None, address=None, qty=2):
        cart = Cart.objects.create(
            user=self.user, currency="USD",
            shipping_address=address, shipping_method=method,
        )
        CartVariantItem.objects.create(cart=cart, variant=self.variant, quantity=qty)
        return cart

    def _method(self, ups_service_code="", base_rate="5.00", free_shipping_threshold=None):
        return ShippingMethod.objects.create(
            zone=self.zone, name="Standard", code=f"m-{ups_service_code or 'flat'}-{free_shipping_threshold or 0}",
            base_rate=Decimal(base_rate), ups_service_code=ups_service_code,
            free_shipping_threshold=Decimal(free_shipping_threshold) if free_shipping_threshold else None,
        )

    def test_no_method_is_free(self):
        cart = self._cart(method=None, address=self.address)
        self.assertEqual(resolve_shipping_amount(cart), Decimal("0.00"))

    def test_subtotal_below_threshold_charges_normally(self):
        # 2 * 19.99 = 39.98, below the 50.00 threshold
        cart = self._cart(method=self._method("", "5.00", free_shipping_threshold="50.00"), address=self.address)
        self.assertEqual(resolve_shipping_amount(cart), Decimal("5.00"))

    def test_subtotal_at_threshold_is_free(self):
        # 2 * 19.99 = 39.98, so a 39.98 threshold is met exactly (>=, not >)
        cart = self._cart(method=self._method("", "5.00", free_shipping_threshold="39.98"), address=self.address)
        self.assertEqual(resolve_shipping_amount(cart), Decimal("0.00"))

    def test_subtotal_above_threshold_is_free(self):
        cart = self._cart(method=self._method("", "5.00", free_shipping_threshold="10.00"), address=self.address)
        self.assertEqual(resolve_shipping_amount(cart), Decimal("0.00"))

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_threshold_met_skips_ups_lookup_entirely(self, mock_rate):
        cart = self._cart(method=self._method("03", "5.00", free_shipping_threshold="10.00"), address=self.address)
        self.assertEqual(resolve_shipping_amount(cart), Decimal("0.00"))
        mock_rate.assert_not_called()

    def test_threshold_flows_into_cart_totals(self):
        cart = self._cart(method=self._method("", "5.00", free_shipping_threshold="10.00"), address=self.address)
        totals = calculate_cart_totals(cart)
        self.assertEqual(totals["shipping_amount"], Decimal("0.00"))
        # tax = 8% of (subtotal - discount + shipping) = 8% of 39.98
        self.assertEqual(totals["tax_amount"], Decimal("3.20"))
        self.assertEqual(totals["grand_total"], Decimal("43.18"))

    def test_method_without_ups_code_uses_base_rate(self):
        cart = self._cart(method=self._method("", "5.00"), address=self.address)
        with patch("apps.cart.services.cart_service.get_rate_for_service") as mock_rate:
            self.assertEqual(resolve_shipping_amount(cart), Decimal("5.00"))
            mock_rate.assert_not_called()  # no UPS call for a flat method

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_ups_method_with_address_returns_live_rate(self, mock_rate):
        mock_rate.return_value = Decimal("12.34")
        cart = self._cart(method=self._method("03", "5.00"), address=self.address)

        self.assertEqual(resolve_shipping_amount(cart), Decimal("12.34"))
        # weight passed to UPS = 200g * 2 = 400g ~ 0.9lb, floored to the 1lb minimum
        packages = mock_rate.call_args.args[1]
        self.assertEqual(packages, [{"weight": "1"}])
        self.assertEqual(mock_rate.call_args.args[2], "03")

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_ups_method_without_address_falls_back_to_base_rate(self, mock_rate):
        cart = self._cart(method=self._method("03", "5.00"), address=None)

        self.assertEqual(resolve_shipping_amount(cart), Decimal("5.00"))
        mock_rate.assert_not_called()

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_international_destination_falls_back_to_base_rate(self, mock_rate):
        intl = Address.objects.create(
            user=self.user, full_name="Pierre", phone="0102030405",
            country="FR", state_province="", city="Paris", postal_code="75001",
            address_line_1="1 Rue de Rivoli",
        )
        cart = self._cart(method=self._method("03", "5.00"), address=intl)

        self.assertEqual(resolve_shipping_amount(cart), Decimal("5.00"))
        mock_rate.assert_not_called()

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_ups_failure_falls_back_to_base_rate(self, mock_rate):
        mock_rate.side_effect = UPSError("boom")
        cart = self._cart(method=self._method("03", "5.00"), address=self.address)

        self.assertEqual(resolve_shipping_amount(cart), Decimal("5.00"))

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_heavier_cart_passes_real_weight(self, mock_rate):
        mock_rate.return_value = Decimal("30.00")
        cart = self._cart(method=self._method("03", "5.00"), address=self.address, qty=20)

        resolve_shipping_amount(cart)
        # 200g * 20 = 4000g -> 8.8 lb
        self.assertEqual(mock_rate.call_args.args[1], [{"weight": "8.8"}])

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_variant_without_weight_uses_default(self, mock_rate):
        self.variant.weight_grams = None
        self.variant.save(update_fields=["weight_grams"])
        mock_rate.return_value = Decimal("10.00")
        cart = self._cart(method=self._method("03", "5.00"), address=self.address, qty=20)

        resolve_shipping_amount(cart)
        # default 150g * 20 = 3000g -> 6.6 lb
        self.assertEqual(mock_rate.call_args.args[1], [{"weight": "6.6"}])

    @patch("apps.cart.services.cart_service.get_rate_for_service")
    def test_live_rate_flows_into_cart_totals_and_tax(self, mock_rate):
        mock_rate.return_value = Decimal("12.34")
        cart = self._cart(method=self._method("03", "5.00"), address=self.address)

        totals = calculate_cart_totals(cart)

        self.assertEqual(totals["subtotal"], Decimal("39.98"))  # 19.99 * 2
        self.assertEqual(totals["shipping_amount"], Decimal("12.34"))
        # tax = 8% of (subtotal - discount + shipping)
        self.assertEqual(totals["tax_amount"], Decimal("4.19"))
        self.assertEqual(totals["grand_total"], Decimal("56.51"))
