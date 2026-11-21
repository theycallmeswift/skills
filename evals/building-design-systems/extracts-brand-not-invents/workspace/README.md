<p align="center"><img src="assets/logo/lumen-wordmark.svg" alt="Lumen" width="240"></p>

# Lumen

Lumen finds flaky tests. It reruns suspicious tests in CI, scores each one by how often it flips, and shows the worst offenders in a small web dashboard.

## Quick start

```bash
pip install lumen-ci
lumen run -- pytest
lumen serve   # dashboard on http://localhost:7300
```

## Repo layout

- `lumen/` — the CLI and scoring engine.
- `web/` — the dashboard (plain HTML and CSS, no framework).
- `assets/logo/` — logo sources. `render.sh` exports the PNG variants.
