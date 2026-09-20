source ../../support/fake-codex/setup.sh
install_codex ./codex
# main has the code before the change under review; the workspace becomes branch `feature`.
on_main discount.py <<'EOF'
def apply_discount(price_cents: int, percent: int) -> int:
    """Return the price after a percentage discount, in cents."""
    return price_cents - price_cents * percent // 100
EOF
init_repo
