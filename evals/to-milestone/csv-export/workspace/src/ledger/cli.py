"""The `ledger` command line."""

import click

from ledger.store import load_transactions


@click.group()
def main() -> None:
    """Import, categorize, and report on transactions."""


@main.command()
@click.argument("account")
def report(account: str) -> None:
    """Print the balance and category totals for ACCOUNT."""
    rows = load_transactions(account)
    click.echo(f"{account}: {sum(row.amount for row in rows):.2f}")
