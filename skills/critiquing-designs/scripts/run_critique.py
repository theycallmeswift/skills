#!/usr/bin/env python3
"""
Run one design rubric against several vision models in parallel and record every reply.

Sends RUBRIC plus the package's manifest-described images (base64) and text files to each
model via the OpenRouter chat-completions API, `--runs` times each. A cost gate runs first:
the estimate (sized from the built content) must fit both --cap and the account balance, or
nothing is sent. Each call's estimate is reserved against the cap and balance before it is
dispatched, and settled with its actual cost after. Every (model, run) pair becomes a JSON
record under OUT_DIR/records/, written as soon as that pair finishes; failures are recorded,
never raised. Transient failures (408, 429, 5xx, timeouts, dropped connections, empty
replies) are retried once after a short pause, and cost is summed over both attempts. A
records/ dir that already holds records is refused unless --only (rerun named pairs) or
--force (overwrite). Stdlib only.

Usage:
    run_critique.py RUBRIC PACKAGE_DIR OUT_DIR --models SLUGS_OR_FILE --cap USD
        [--runs 2] [--only SLUG#RUN,...] [--force] [--base-url URL] [--estimate-only]
        [--workers 12]
    --models is a comma list or a file with one slug per line (# comments ok).
    Base URL: --base-url, else $OPENROUTER_BASE_URL, else https://openrouter.ai/api/v1.
    Key: $OPENROUTER_API_KEY.
Exit codes: 0 all runs parsed; 1 some run failed or did not parse; 2 usage or input error;
3 cost gate refused (also with --estimate-only, which makes no completion call either way).
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 32000  # reasoning models spend most of this thinking before the JSON reply
CALL_TIMEOUT_SECONDS = 900
META_TIMEOUT_SECONDS = 60
RETRY_DELAY_SECONDS = 3.0
RETRYABLE_STATUSES = {408, 429}
# Pricing assumptions behind the cost estimate, per call.
MIN_PROMPT_TOKENS = 40000
TOKENS_PER_IMAGE = 1600
CHARS_PER_TOKEN = 4
ESTIMATED_COMPLETION_TOKENS = 8000
COST_EPSILON = 1e-9
SKIPPED_ERROR = "skipped: spend cap reached"
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
TEXT_SUFFIXES = {".md", ".txt", ".json"}
MANIFEST_NAME = "manifest.json"
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_COST_GATE = 3


class UsageError(Exception):
    """Bad arguments, package contents, or an unusable API; maps to exit 2."""


@dataclass
class Pair:
    """One (model, run) call."""

    model: str
    run: int

    @property
    def label(self) -> str:
        """The `slug#run` spelling used by --only and the summary line."""
        return f"{self.model}#{self.run}"

    def record_name(self) -> str:
        """The record file name, with / in the slug replaced by __."""
        return f"{self.model.replace('/', '__')}__run{self.run}.json"


@dataclass
class Spend:
    """Thread-safe spend ledger: settled cost plus in-flight reservations against a limit."""

    limit: float
    total: float = 0.0
    reserved: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def reserve(self, amount: float) -> bool:
        """Hold amount for a call about to start; False when it would pass the limit."""
        with self.lock:
            if self.total + self.reserved + amount > self.limit + COST_EPSILON:
                return False
            self.reserved += amount
            return True

    def settle(self, reserved: float, actual: float) -> None:
        """Release a reservation and record what the call actually cost."""
        with self.lock:
            self.reserved -= reserved
            self.total += actual


@dataclass
class Gate:
    """The cost gate's verdict: fits the budget, the balance seen, and each pair's estimate."""

    within_budget: bool
    balance: float
    pair_costs: dict[str, float]


@dataclass
class CallResult:
    """Outcome of one HTTP attempt; status is None when no response arrived."""

    status: int | None
    body: dict | None
    error: str | None
    raw_body: str = ""


def parse_models(spec: str) -> list[str]:
    """Read model slugs from a comma list or from a file with one slug per line."""
    path = Path(spec)
    if path.is_file():
        lines = (line.split("#", 1)[0].strip() for line in path.read_text().splitlines())
        slugs = [line for line in lines if line]
    else:
        slugs = [slug.strip() for slug in spec.split(",") if slug.strip()]
    if not slugs:
        raise UsageError("--models named no models")
    return slugs


def parse_only(spec: str, models: list[str], runs: int) -> list[Pair]:
    """Parse `slug#run,...` into pairs, checking each exists in models x runs."""
    pairs = []
    for item in spec.split(","):
        slug, separator, run_text = item.strip().rpartition("#")
        if not separator or not run_text.isdigit():
            raise UsageError(f"--only entries look like slug#run, got {item!r}")
        pair = Pair(model=slug, run=int(run_text))
        if pair.model not in models or not 1 <= pair.run <= runs:
            raise UsageError(f"--only names a pair outside --models x --runs: {item!r}")
        pairs.append(pair)
    return pairs


def _data_url(path: Path) -> str:
    """Encode an image file as a base64 data URL."""
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def load_manifest(package_dir: Path) -> list[dict]:
    """Read manifest.json: a list of {file, frame, theme, description}."""
    manifest_path = package_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        raise UsageError(f"no {MANIFEST_NAME} in {package_dir}")
    try:
        entries = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as error:
        raise UsageError(f"{manifest_path} is not valid JSON: {error}") from error
    if not isinstance(entries, list):
        raise UsageError(f"{manifest_path} must be a list")
    return entries


def build_content(rubric: str, package_dir: Path) -> list[dict]:
    """Build the user message parts: rubric, manifest images in order, then text files."""
    entries = load_manifest(package_dir)
    parts: list[dict] = [{"type": "text", "text": rubric}]
    listed = {MANIFEST_NAME}
    for entry in entries:
        image_path = package_dir / entry["file"]
        if not image_path.is_file():
            raise UsageError(f"manifest names a missing file: {entry['file']}")
        listed.add(entry["file"])
        caption = f"[{entry['frame']}] ({entry['theme']}): {entry['description']}"
        parts.append({"type": "text", "text": caption})
        parts.append({"type": "image_url", "image_url": {"url": _data_url(image_path)}})
    for path in sorted(package_dir.iterdir()):
        if path.suffix in TEXT_SUFFIXES and path.name not in listed:
            parts.append({"type": "text", "text": f"[{path.name}]\n{path.read_text()}"})
    return parts


def request_json(
    url: str, api_key: str, body: dict | None = None, timeout: int = META_TIMEOUT_SECONDS
) -> CallResult:
    """GET (or POST when body is given) and decode a JSON reply; transport errors are returned."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data)
    request.add_header("Authorization", f"Bearer {api_key}")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _decode(response.status, response.read())
    except urllib.error.HTTPError as error:
        return _decode(error.code, error.read())
    except (urllib.error.URLError, OSError, http.client.HTTPException) as error:
        return CallResult(status=None, body=None, error=f"{type(error).__name__}: {error}")


def _decode(status: int, payload: bytes) -> CallResult:
    """Wrap a response, decoding its JSON body when there is one."""
    text = payload.decode("utf-8", errors="replace")
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = None
    body = decoded if isinstance(decoded, dict) else None
    return CallResult(status=status, body=body, error=None, raw_body=text)


def fetch_balance(base_url: str, api_key: str) -> float:
    """Return remaining credits in USD (total credits minus usage)."""
    result = request_json(f"{base_url}/credits", api_key)
    if result.status != 200 or result.body is None:
        raise UsageError(f"could not read credits: {result.error or result.status}")
    data = result.body["data"]
    return float(data["total_credits"]) - float(data["total_usage"])


def _price(model: dict, key: str) -> float | None:
    """One per-token price from a catalog entry, or None when null, missing or negative."""
    pricing = model.get("pricing")
    value = pricing.get(key) if isinstance(pricing, dict) else None
    if not isinstance(value, int | float | str):
        return None
    try:
        price = float(value)
    except ValueError:
        return None
    return price if price >= 0 else None


def fetch_prices(base_url: str, api_key: str) -> dict[str, tuple[float, float] | None]:
    """Return {slug: (prompt $/token, completion $/token)}; None marks unusable pricing."""
    result = request_json(f"{base_url}/models", api_key)
    if result.status != 200 or result.body is None:
        raise UsageError(f"could not list models: {result.error or result.status}")
    prices: dict[str, tuple[float, float] | None] = {}
    for model in result.body["data"]:
        prompt, completion = _price(model, "prompt"), _price(model, "completion")
        prices[model["id"]] = None if prompt is None or completion is None else (prompt, completion)
    return prices


def estimate_prompt_tokens(content: list[dict]) -> int:
    """Size one call's prompt: text chars / 4 plus a constant per image, floored at 40k."""
    characters = sum(len(part.get("text", "")) for part in content if part["type"] == "text")
    images = sum(1 for part in content if part["type"] == "image_url")
    return max(MIN_PROMPT_TOKENS, characters // CHARS_PER_TOKEN + TOKENS_PER_IMAGE * images)


def estimate_pair_cost(prices: tuple[float, float], prompt_tokens: int) -> float:
    """Estimate one call's USD from its model's per-token prices."""
    return prompt_tokens * prices[0] + ESTIMATED_COMPLETION_TOKENS * prices[1]


def _json_objects(text: str) -> list[dict]:
    """Every top-level JSON object in text, in order, skipping prose and unparsable braces."""
    decoder = json.JSONDecoder()
    found: list[dict] = []
    position = text.find("{")
    while position != -1:
        try:
            parsed, end = decoder.raw_decode(text, position)
        except json.JSONDecodeError:
            position = text.find("{", position + 1)
            continue
        if isinstance(parsed, dict):
            found.append(parsed)
        position = text.find("{", end)
    return found


def extract_json(text: str) -> dict | None:
    """Parse the critique object from reply text.

    Tolerates code fences, prose and <think> blocks. Tries every "{" in order and returns
    the first object with an "issues" key. Any other object (a nested fragment of a
    truncated reply, say) is not a critique, so the run stays unparsed and its raw text
    goes to synthesis.
    """
    for candidate in (THINK_BLOCK.sub("", text), text):
        for parsed in _json_objects(candidate):
            if "issues" in parsed:
                return parsed
    return None


def _http_error_text(result: CallResult) -> str:
    """Describe a non-200 reply as a record error string."""
    if result.status == 402:
        return "insufficient credits (402)"
    return f"HTTP {result.status}: {result.raw_body[:300]}"


def _is_retryable(result: CallResult, content: str | None) -> bool:
    """Retry transport failures, 408, 429, 5xx and empty replies; never other client errors."""
    if result.status is None:
        return True
    if result.status in RETRYABLE_STATUSES or result.status >= 500:
        return True
    return result.status == 200 and not content


def _content_of(result: CallResult) -> str | None:
    """Pull the assistant message text from a completion reply."""
    if result.body is None:
        return None
    try:
        return result.body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def _cost_of(result: CallResult) -> float:
    """The billed USD in a reply's usage block, 0 when absent or malformed."""
    usage = (result.body or {}).get("usage")
    try:
        return float(usage.get("cost") or 0) if isinstance(usage, dict) else 0.0
    except (TypeError, ValueError):
        return 0.0


def pause(seconds: float) -> None:
    """Sleep between attempts; a seam so tests stay fast."""
    time.sleep(seconds)


def attempt_with_retry(
    url: str, api_key: str, body: dict, spend: Spend, estimate: float
) -> tuple[CallResult | None, str | None, float]:
    """Make the call, retrying once after a pause; each attempt reserves its estimate first.

    Returns (last result, its content, cost summed over attempts). The result is None when the
    spend limit blocked the first attempt; a blocked retry keeps the first attempt's result.
    """
    result: CallResult | None = None
    content: str | None = None
    cost = 0.0
    for attempt in (1, 2):
        if not spend.reserve(estimate):
            break
        actual = 0.0
        try:
            result = request_json(url, api_key, body, timeout=CALL_TIMEOUT_SECONDS)
            content = _content_of(result)
            actual = _cost_of(result)
        finally:
            spend.settle(estimate, actual)
        cost += actual
        if attempt == 2 or not _is_retryable(result, content):
            break
        pause(RETRY_DELAY_SECONDS)
    return result, content, cost


def build_record(
    pair: Pair, result: CallResult, content: str | None, seconds: float, cost: float | None = None
) -> dict:
    """Turn the final attempt into the record dict; errors become fields, never raises."""
    body = result.body or {}
    usage = body.get("usage") or {}
    choices = body.get("choices") or [{}]
    error = result.error
    if error is None and result.status != 200:
        error = _http_error_text(result)
    elif error is None and not content:
        error = "empty reply"
    return {
        "model": pair.model,
        "run": pair.run,
        "ok": error is None,
        "error": error,
        "status": result.status,
        "raw_text": content,
        "parsed": extract_json(content) if content else None,
        "cost_usd": _cost_of(result) if cost is None else cost,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "seconds": round(seconds, 2),
        "finish_reason": choices[0].get("finish_reason"),
    }


def _call_pair(
    pair: Pair, base_url: str, api_key: str, content: list[dict], spend: Spend, estimate: float
) -> dict:
    """Call one model (with its retry) and return its record."""
    request_body = {
        "model": pair.model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": MAX_TOKENS,
        "reasoning": {"effort": "medium"},
        "usage": {"include": True},
    }
    started = time.monotonic()
    result, reply, cost = attempt_with_retry(
        f"{base_url}/chat/completions", api_key, request_body, spend, estimate
    )
    if result is None:
        return build_record(pair, CallResult(None, None, SKIPPED_ERROR), None, 0.0)
    return build_record(pair, result, reply, time.monotonic() - started, cost)


def run_pair(
    pair: Pair,
    base_url: str,
    api_key: str,
    content: list[dict],
    spend: Spend,
    estimate: float,
    records_dir: Path,
) -> dict:
    """Run one pair, turn any exception into an error record, and write the record at once."""
    try:
        record = _call_pair(pair, base_url, api_key, content, spend, estimate)
    except Exception as error:
        failure = CallResult(status=None, body=None, error=f"{type(error).__name__}: {error}")
        record = build_record(pair, failure, None, 0.0)
    write_record(records_dir, pair, record)
    return record


def write_record(records_dir: Path, pair: Pair, record: dict) -> None:
    """Write one record file, overwriting any earlier one."""
    (records_dir / pair.record_name()).write_text(json.dumps(record, indent=2) + "\n")


def summarize(records_dir: Path, pairs: list[Pair], seconds: float) -> dict:
    """Aggregate the records of pairs in the plan (so --only reruns update the totals).

    Records for pairs outside the plan, such as models dropped since an earlier run, are
    ignored; pairs with no record yet are skipped.
    """
    paths = [records_dir / pair.record_name() for pair in pairs]
    records = [json.loads(path.read_text()) for path in paths if path.is_file()]
    failed = [f"{record['model']}#{record['run']}" for record in records if not record["ok"]]
    unparsed = [
        f"{record['model']}#{record['run']}"
        for record in records
        if record["ok"] and record["parsed"] is None
    ]
    return {
        "total_cost_usd": round(sum(record["cost_usd"] for record in records), 6),
        "seconds": round(seconds, 1),
        "runs": len(records),
        "parsed_runs": sum(1 for record in records if record["parsed"] is not None),
        "failed": failed,
        "unparsed": unparsed,
    }


def all_pairs(models: list[str], runs: int) -> list[Pair]:
    """Every model x run pair: the full plan, whatever subset --only reruns."""
    return [Pair(model=model, run=run) for model in models for run in range(1, runs + 1)]


def plan_pairs(args: argparse.Namespace, models: list[str]) -> list[Pair]:
    """Choose the pairs to run: the --only list, or every model x run."""
    if args.only:
        return parse_only(args.only, models, args.runs)
    return all_pairs(models, args.runs)


def check_cost_gate(
    args: argparse.Namespace,
    base_url: str,
    api_key: str,
    pairs: list[Pair],
    models: list[str],
    content: list[dict],
) -> Gate:
    """Print the estimate and report whether the run fits the cap and the balance."""
    prices = fetch_prices(base_url, api_key)
    unknown = [model for model in models if model not in prices]
    if unknown:
        raise UsageError(f"unknown model slugs: {', '.join(unknown)}")
    unpriced = [model for model in models if prices[model] is None]
    if unpriced:
        raise UsageError(
            f"null or negative pricing for: {', '.join(unpriced)}; pick a model with fixed prices"
        )
    balance = fetch_balance(base_url, api_key)
    prompt_tokens = estimate_prompt_tokens(content)
    pair_costs = {}
    for pair in pairs:
        model_prices = prices[pair.model]
        assert model_prices is not None
        pair_costs[pair.label] = estimate_pair_cost(model_prices, prompt_tokens)
    estimate = sum(pair_costs.values())
    print(f"models {', '.join(models)}")
    print(f"estimate ${estimate:.2f}  cap ${args.cap:.2f}  balance ${balance:.2f}")
    if estimate > args.cap:
        print(f"refusing: estimate ${estimate:.2f} exceeds cap ${args.cap:.2f}")
        return Gate(False, balance, pair_costs)
    if estimate > balance:
        print(f"refusing: estimate ${estimate:.2f} exceeds balance ${balance:.2f}")
        return Gate(False, balance, pair_costs)
    return Gate(True, balance, pair_costs)


def refuse_existing_records(records_dir: Path, args: argparse.Namespace) -> None:
    """Refuse to overwrite earlier records unless the run is --only or --force."""
    if args.only or args.force or not records_dir.is_dir():
        return
    if any(records_dir.glob("*.json")):
        raise UsageError(
            f"{records_dir} already holds records; pass --only to rerun named pairs, "
            "--force to overwrite, or pick a new OUT_DIR"
        )


def execute(args: argparse.Namespace) -> int:
    """Validate inputs, pass the cost gate, run all pairs, write records and stats."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise UsageError("OPENROUTER_API_KEY is not set")
    base_url = (args.base_url or os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL).rstrip(
        "/"
    )
    models = parse_models(args.models)
    pairs = plan_pairs(args, models)
    rubric = Path(args.rubric).read_text()
    content = build_content(rubric, Path(args.package_dir))
    records_dir = Path(args.out_dir) / "records"
    if not args.estimate_only:
        refuse_existing_records(records_dir, args)

    gate = check_cost_gate(args, base_url, api_key, pairs, models, content)
    if not gate.within_budget:
        return EXIT_COST_GATE
    if args.estimate_only:
        return 0

    records_dir.mkdir(parents=True, exist_ok=True)
    spend = Spend(limit=min(args.cap, gate.balance))
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                run_pair,
                pair,
                base_url,
                api_key,
                content,
                spend,
                gate.pair_costs[pair.label],
                records_dir,
            )
            for pair in pairs
        ]
        for future in futures:
            future.result()

    stats = summarize(records_dir, all_pairs(models, args.runs), time.monotonic() - started)
    (Path(args.out_dir) / "run_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    summary = (
        f"parsed {stats['parsed_runs']}/{stats['runs']} runs, ${stats['total_cost_usd']:.2f}, "
        f"{stats['seconds']:.0f}s"
    )
    if stats["failed"]:
        summary += f"; rerun failures with --only {','.join(stats['failed'])}"
    if stats["unparsed"]:
        summary += f"; unparsed (read raw_text, don't rerun): {','.join(stats['unparsed'])}"
    print(summary)
    return 0 if not stats["failed"] and not stats["unparsed"] else EXIT_FAILED


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description="Run a design rubric across vision models.")
    parser.add_argument("rubric")
    parser.add_argument("package_dir")
    parser.add_argument("out_dir")
    parser.add_argument("--models", required=True)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--cap", type=float, required=True, help="USD spend cap")
    parser.add_argument("--only", help="comma list of slug#run pairs to (re)run")
    parser.add_argument("--force", action="store_true", help="overwrite existing records")
    parser.add_argument("--base-url")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args(argv)

    try:
        return execute(args)
    except (UsageError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
