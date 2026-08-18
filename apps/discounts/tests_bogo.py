"""Edge-case coverage for the buy-X-get-Y pricing engine.

These exercise `compute_bogo_discount` directly — it is a pure function, so every
case here runs without database setup.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from .services.bogo_service import (
    BogoConfig,
    CartLine,
    DiscountScope,
    compute_bogo_discount,
)


def line(key, price, qty, product_id=None, category_ids=(), bundle_id=None):
    return CartLine(
        key=key,
        unit_price=Decimal(price),
        quantity=qty,
        product_id=product_id,
        bundle_id=bundle_id,
        category_ids=frozenset(category_ids),
    )


BUY_2_GET_1 = BogoConfig(buy_quantity=2, get_quantity=1)


class SharedPoolTests(SimpleTestCase):
    """Reward drawn from the same pool the customer buys from."""

    def test_exactly_one_group_gives_one_free_unit(self):
        result = compute_bogo_discount([line("a", "10.00", 3)], BUY_2_GET_1)
        self.assertEqual(result.discount_amount, Decimal("10.00"))
        self.assertEqual(result.free_units, 1)
        self.assertEqual(result.applications, 1)

    def test_below_group_size_gives_nothing(self):
        # Buy 2 get 1 needs 3 units in the cart, not 2.
        result = compute_bogo_discount([line("a", "10.00", 2)], BUY_2_GET_1)
        self.assertEqual(result.discount_amount, Decimal("0.00"))
        self.assertFalse(result.applies)

    def test_partial_second_group_does_not_round_up(self):
        result = compute_bogo_discount([line("a", "10.00", 5)], BUY_2_GET_1)
        self.assertEqual(result.free_units, 1)
        self.assertEqual(result.discount_amount, Decimal("10.00"))

    def test_repeats_for_every_full_group(self):
        result = compute_bogo_discount([line("a", "10.00", 6)], BUY_2_GET_1)
        self.assertEqual(result.applications, 2)
        self.assertEqual(result.discount_amount, Decimal("20.00"))

    def test_cheapest_units_are_the_free_ones(self):
        lines = [line("cheap", "5.00", 1), line("mid", "12.00", 1), line("pricey", "30.00", 1)]
        result = compute_bogo_discount(lines, BUY_2_GET_1)
        # The customer must not get the £30 item free while a £5 one is present.
        self.assertEqual(result.discount_amount, Decimal("5.00"))
        self.assertEqual(result.line_allocations, {"cheap": Decimal("5.00")})

    def test_free_units_span_multiple_lines(self):
        lines = [line("a", "4.00", 2), line("b", "9.00", 4)]
        result = compute_bogo_discount(lines, BogoConfig(buy_quantity=1, get_quantity=1))
        # 6 units -> 3 groups -> 3 free: both £4 units and one £9 unit.
        self.assertEqual(result.free_units, 3)
        self.assertEqual(result.discount_amount, Decimal("17.00"))
        self.assertEqual(result.line_allocations["a"], Decimal("8.00"))
        self.assertEqual(result.line_allocations["b"], Decimal("9.00"))

    def test_empty_cart(self):
        self.assertFalse(compute_bogo_discount([], BUY_2_GET_1).applies)

    def test_zero_priced_units_are_ignored(self):
        # A £0 line must not soak up a reward that the paying units earned.
        lines = [line("free", "0.00", 5), line("paid", "10.00", 3)]
        result = compute_bogo_discount(lines, BUY_2_GET_1)
        self.assertEqual(result.discount_amount, Decimal("10.00"))
        self.assertNotIn("free", result.line_allocations)

    def test_zero_quantity_line_is_ignored(self):
        result = compute_bogo_discount([line("a", "10.00", 0), line("b", "10.00", 3)], BUY_2_GET_1)
        self.assertEqual(result.discount_amount, Decimal("10.00"))


class ConfigurationTests(SimpleTestCase):
    def test_max_applications_caps_repeats(self):
        config = BogoConfig(buy_quantity=2, get_quantity=1, max_applications=1)
        result = compute_bogo_discount([line("a", "10.00", 9)], config)
        self.assertEqual(result.applications, 1)
        self.assertEqual(result.discount_amount, Decimal("10.00"))

    def test_partial_reward_percentage(self):
        config = BogoConfig(buy_quantity=1, get_quantity=1, reward_percentage=Decimal("50.00"))
        result = compute_bogo_discount([line("a", "20.00", 2)], config)
        self.assertEqual(result.discount_amount, Decimal("10.00"))

    def test_zero_reward_percentage_is_inert(self):
        config = BogoConfig(buy_quantity=1, get_quantity=1, reward_percentage=Decimal("0"))
        self.assertFalse(compute_bogo_discount([line("a", "20.00", 4)], config).applies)

    def test_zero_buy_quantity_cannot_give_free_items(self):
        # Guards the "buy 0 get 1 free" misconfiguration that would empty stock.
        config = BogoConfig(buy_quantity=0, get_quantity=1)
        self.assertFalse(compute_bogo_discount([line("a", "10.00", 5)], config).applies)

    def test_get_more_than_buy(self):
        config = BogoConfig(buy_quantity=1, get_quantity=2)
        result = compute_bogo_discount([line("a", "10.00", 6)], config)
        # Group size is 3, so 6 units = 2 groups = 4 free units.
        self.assertEqual(result.free_units, 4)
        self.assertEqual(result.discount_amount, Decimal("40.00"))

    def test_rounding_is_half_up_per_unit(self):
        config = BogoConfig(buy_quantity=1, get_quantity=1, reward_percentage=Decimal("33.33"))
        result = compute_bogo_discount([line("a", "10.01", 2)], config)
        self.assertEqual(result.discount_amount, Decimal("3.34"))


class ScopeTests(SimpleTestCase):
    def test_product_scope_excludes_other_products(self):
        config = BogoConfig(
            buy_quantity=2,
            get_quantity=1,
            eligible_scope=DiscountScope(product_ids=frozenset({1})),
        )
        lines = [line("in", "10.00", 3, product_id=1), line("out", "1.00", 5, product_id=2)]
        result = compute_bogo_discount(lines, config)
        # The cheap out-of-scope units must not be given away.
        self.assertEqual(result.discount_amount, Decimal("10.00"))
        self.assertEqual(list(result.line_allocations), ["in"])

    def test_category_scope_matches(self):
        config = BogoConfig(
            buy_quantity=1,
            get_quantity=1,
            eligible_scope=DiscountScope(category_ids=frozenset({7})),
        )
        lines = [line("socks", "8.00", 2, product_id=1, category_ids=(7, 9))]
        self.assertEqual(compute_bogo_discount(lines, config).discount_amount, Decimal("8.00"))

    def test_out_of_scope_cart_earns_nothing(self):
        config = BogoConfig(
            buy_quantity=1,
            get_quantity=1,
            eligible_scope=DiscountScope(product_ids=frozenset({99})),
        )
        self.assertFalse(compute_bogo_discount([line("a", "10.00", 4, product_id=1)], config).applies)


class SeparateRewardPoolTests(SimpleTestCase):
    """"Buy 3 socks, get a cap free" — buy set and reward set are different."""

    config = BogoConfig(
        buy_quantity=3,
        get_quantity=1,
        eligible_scope=DiscountScope(product_ids=frozenset({1})),
        reward_scope=DiscountScope(product_ids=frozenset({2})),
    )

    def test_reward_needs_no_extra_buy_units(self):
        lines = [line("socks", "10.00", 3, product_id=1), line("cap", "25.00", 1, product_id=2)]
        result = compute_bogo_discount(lines, self.config)
        # 3 socks is enough; the cap does not have to be a 4th eligible unit.
        self.assertEqual(result.discount_amount, Decimal("25.00"))

    def test_no_reward_item_in_cart_gives_nothing(self):
        lines = [line("socks", "10.00", 6, product_id=1)]
        self.assertFalse(compute_bogo_discount(lines, self.config).applies)

    def test_free_units_capped_by_available_reward_stock(self):
        # Earns 2 applications but only one cap is in the cart.
        lines = [line("socks", "10.00", 6, product_id=1), line("cap", "25.00", 1, product_id=2)]
        result = compute_bogo_discount(lines, self.config)
        self.assertEqual(result.applications, 2)
        self.assertEqual(result.free_units, 1)
        self.assertEqual(result.discount_amount, Decimal("25.00"))

    def test_cheapest_reward_chosen_when_several(self):
        lines = [
            line("socks", "10.00", 3, product_id=1),
            line("cap-cheap", "15.00", 1, product_id=2),
            line("cap-pricey", "40.00", 1, product_id=2),
        ]
        result = compute_bogo_discount(lines, self.config)
        self.assertEqual(result.discount_amount, Decimal("15.00"))


class BundleTests(SimpleTestCase):
    def test_bundle_line_can_be_scoped_in(self):
        config = BogoConfig(
            buy_quantity=1,
            get_quantity=1,
            eligible_scope=DiscountScope(bundle_ids=frozenset({5})),
        )
        result = compute_bogo_discount([line("b", "30.00", 2, bundle_id=5)], config)
        self.assertEqual(result.discount_amount, Decimal("30.00"))

    def test_unscoped_offer_covers_bundles_and_variants_alike(self):
        lines = [line("v", "10.00", 1, product_id=1), line("b", "4.00", 1, bundle_id=5)]
        result = compute_bogo_discount(lines, BogoConfig(buy_quantity=1, get_quantity=1))
        self.assertEqual(result.discount_amount, Decimal("4.00"))
