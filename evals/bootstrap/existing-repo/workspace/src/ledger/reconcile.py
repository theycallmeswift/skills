"""Match bank export rows to ledger entries."""


def unmatched(bank_amounts: list[int], ledger_amounts: list[int]) -> list[int]:
    """Return bank amounts with no equal ledger amount, in input order."""
    remaining = list(ledger_amounts)
    missing = []
    for amount in bank_amounts:
        if amount in remaining:
            remaining.remove(amount)
        else:
            missing.append(amount)

    return missing
