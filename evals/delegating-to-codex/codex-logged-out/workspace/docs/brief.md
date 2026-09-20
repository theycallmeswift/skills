# Brief: retry helper

Create `retry.py` with `retry(fn, attempts=3, base_delay=0.1)` that calls `fn`, retrying on
any exception with exponential backoff (`base_delay * 2**n`), and re-raises the last
exception after the final attempt. Add `test_retry.py` covering success on the second try
and exhaustion.
