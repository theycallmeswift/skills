def apply_discount(price_cents: int, percent: int) -> int:
    """Return the price after a percentage discount, in cents."""
    return price_cents - price_cents * percent // 100


def apply_coupon(price_cents: int, coupon: dict) -> int:
    """Apply a coupon: {"kind": "percent"|"fixed", "value": int}."""
    if coupon["kind"] == "percent":
        return apply_discount(price_cents, coupon["value"])
    return price_cents - coupon["value"]
