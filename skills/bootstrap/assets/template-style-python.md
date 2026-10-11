# Python style

Apply this guide after [development.md](development.md). `make lint` checks it
with Ruff and ty.

- **Typed throughout.** Parse untyped input (JSON, YAML, HTTP bodies) at the
  boundary into dataclasses, or narrow it with `isinstance`; never let `Any`
  travel inward.
- **Dataclasses for data, `Protocol` for seams,** so a test fake satisfies a
  seam structurally.
- **Google-style docstrings** on every module, class, and function. Test
  functions skip them; the name states the behavior.
- **`pathlib` for paths,** and `encoding="utf-8"` on every text read and write.
- **Keyword-only arguments** (`*,`) once a function takes more than two
  parameters of the same type.
- **Errors are exception classes named for the domain,** with messages that
  name the file or field at fault.
- **Command-line output goes through a logger,** never `print`.
- **uv owns the environment.** Add dependencies with `uv add`; never
  `pip install` into `.venv`.

```python
@pytest.mark.parametrize(
    ("bank", "ledger", "unmatched_amounts"),
    [
        ([100, 200], [200, 100], []),
        ([300, 100], [100], [300]),
        ([100, 100], [100], [100]),
    ],
)
def test_reports_bank_amounts_with_no_ledger_match(
    bank: list[int], ledger: list[int], unmatched_amounts: list[int]
) -> None:
    assert unmatched(bank, ledger) == unmatched_amounts
```
