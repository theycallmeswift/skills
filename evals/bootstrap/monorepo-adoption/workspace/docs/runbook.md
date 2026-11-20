# Runbook

The Worker serves the latest digest from the `DIGESTS` namespace.

The pipeline runs nightly from the scheduler, which calls `uv run --directory pipeline python -m pipeline.ingest`.

To publish these docs, run `scripts/publish-docs.sh`.
