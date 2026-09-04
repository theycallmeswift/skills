# API Server

A small HTTP API. The request lifecycle lives in `app/server.py` (`handle_request`).

Logging today is a single unstructured `print()` per request. We want structured
logging, but a few decisions are still open.
