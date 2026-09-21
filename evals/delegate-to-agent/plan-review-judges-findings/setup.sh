source ../../support/fake-codex/setup.sh
install_codex ./codex
# main has the code before the change under review; the workspace becomes branch `feature`.
on_main pager.py <<'EOF'
def page_slice(items: list, page: int, size: int) -> list:
    """Return the 1-indexed page of items."""
    start = (page - 1) * size
    return items[start:start + size]
EOF
init_repo
