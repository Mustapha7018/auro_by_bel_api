"""Single source of truth for deposit pricing.

A pre-order / booking deposit is always this fraction of the item price, so the
amount shown to customers is a real percentage of what they see (not a
hand-typed number)."""

DEPOSIT_RATE = 1 / 3  # one-third (≈33%)


def deposit_for(price: float | None) -> float:
    return round((price or 0) * DEPOSIT_RATE)
