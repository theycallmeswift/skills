"""HTTP request lifecycle. One unstructured print per request today."""

from __future__ import annotations

import time


def handle_request(method: str, path: str, handler) -> object:
    start = time.monotonic()
    status, body = handler()
    latency_ms = (time.monotonic() - start) * 1000
    print(f"{method} {path} -> {status} ({latency_ms:.1f}ms)")
    return body
