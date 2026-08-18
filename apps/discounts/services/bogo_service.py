"""Buy X get Y pricing engine.

The core (`compute_bogo_discount`) is a pure function over plain cart lines so it
can be unit tested without the ORM, mirrored on the storefront for guest carts,
and reused for order previews. Nothing about an applied offer is persisted on the
cart: the reward is recomputed from the cart's current contents every time totals
are calculated, so quantity edits, removals and price changes can never leave a
stale free item behind.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Sequence

MONEY_QUANT = Decimal("0.01")
FULL_PERCENT = Decimal("100.00")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CartLine:
    """One cart row, flattened for pricing.

    `key` identifies the row for the caller (so a per-line allocation can be
    mapped back onto a CartVariantItem/OrderItem). `product_id`, `category_ids`
    and `bundle_id` exist only for scope matching.
    """

    key: str
    unit_price: Decimal
    quantity: int
    product_id: int | None = None
    bundle_id: int | None = None
    category_ids: frozenset[int] = frozenset()


@dataclass(frozen=True)
class DiscountScope:
    """Which catalogue entries a rule set covers. Empty = the whole cart."""

    product_ids: frozenset[int] = frozenset()
    bundle_ids: frozenset[int] = frozenset()
    category_ids: frozenset[int] = frozenset()

    @property
    def is_empty(self) -> bool:
        return not (self.product_ids or self.bundle_ids or self.category_ids)

    def matches(self, line: CartLine) -> bool:
        if self.is_empty:
            return True
        if line.product_id is not None and line.product_id in self.product_ids:
            return True
        if line.bundle_id is not None and line.bundle_id in self.bundle_ids:
            return True
        return bool(self.category_ids & line.category_ids)


@dataclass(frozen=True)
class BogoConfig:
    buy_quantity: int
    get_quantity: int
    reward_percentage: Decimal = FULL_PERCENT
    max_applications: int | None = None
    # When the reward scope is empty the reward is drawn from the eligible pool
    # itself ("buy 2 get 1 free" on one product line). When it is populated the
    # two pools are separate ("buy 3 socks, get a cap free").
    eligible_scope: DiscountScope = DiscountScope()
    reward_scope: DiscountScope | None = None


@dataclass
class BogoResult:
    discount_amount: Decimal = Decimal("0.00")
    free_units: int = 0
    applications: int = 0
    # key -> amount discounted on that line, for per-line order records.
    line_allocations: dict[str, Decimal] = field(default_factory=dict)

    @property
    def applies(self) -> bool:
        return self.discount_amount > 0


def _expand_units(lines: Iterable[CartLine]) -> list[tuple[Decimal, str]]:
    """One entry per physical unit, as (unit_price, line_key)."""
    units: list[tuple[Decimal, str]] = []
    for line in lines:
        if line.quantity <= 0 or line.unit_price <= 0:
            # A zero-priced or empty row can never fund or receive a reward, and
            # letting it through would let free units be "spent" on nothing.
            continue
        units.extend([(line.unit_price, line.key)] * line.quantity)
    return units


def compute_bogo_discount(lines: Sequence[CartLine], config: BogoConfig) -> BogoResult:
    """Return the discount earned by a buy-X-get-Y offer on `lines`.

    Reward units are always taken cheapest-first. That is both the customer-safe
    reading of "get one free" (you do not get the most expensive item free unless
    it is the only one left) and the bound on what the offer can cost.
    """
    result = BogoResult()

    if config.buy_quantity < 1 or config.get_quantity < 1:
        return result
    if config.reward_percentage <= 0:
        return result

    eligible_lines = [line for line in lines if config.eligible_scope.matches(line)]
    eligible_units = _expand_units(eligible_lines)
    if not eligible_units:
        return result

    separate_reward_pool = config.reward_scope is not None and not config.reward_scope.is_empty

    if separate_reward_pool:
        reward_lines = [line for line in lines if config.reward_scope.matches(line)]
        reward_units = _expand_units(reward_lines)
        # The buy set and the reward set are independent, so every full group of
        # `buy_quantity` eligible units earns an application.
        applications = len(eligible_units) // config.buy_quantity
    else:
        # Shared pool: a "buy 2 get 1 free" group consumes 3 units, so the
        # customer must have 3 in the cart before anything is free.
        reward_units = eligible_units
        group_size = config.buy_quantity + config.get_quantity
        applications = len(eligible_units) // group_size

    if applications < 1:
        return result

    if config.max_applications is not None:
        applications = min(applications, config.max_applications)

    free_units = applications * config.get_quantity
    # Never promise more free units than there are items to give away.
    free_units = min(free_units, len(reward_units))
    if free_units < 1:
        return result

    # Cheapest first — sorted on price only; the key is carried along.
    cheapest = sorted(reward_units, key=lambda unit: unit[0])[:free_units]

    rate = config.reward_percentage / FULL_PERCENT
    total = Decimal("0.00")
    for unit_price, key in cheapest:
        amount = _money(unit_price * rate)
        total += amount
        result.line_allocations[key] = result.line_allocations.get(key, Decimal("0.00")) + amount

    result.discount_amount = _money(total)
    result.free_units = free_units
    result.applications = applications
    return result
