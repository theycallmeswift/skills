# Testing & Eval Strategy

**Date:** 2026-04-09
**Status:** Approved

## Goal

A pytest-based eval suite for MechaSwift skills that verifies rule compliance and content preservation. Starting with ghostwrite only. Tests must be fast and pass with a cheap model (haiku).

## Non-Goals

- Voice/tone quality scoring (future round, requires LLM judge tuning)
- Skill triggering tests (existing eval harness in `.claude/skills/skill-creator/` covers this)
- Tests for skills other than ghostwrite (add later as the pattern proves out)
- CI integration (local-first for now)

## Approach

Three-layer architecture: a generic Claude CLI test harness, a library of assertion helpers (deterministic + LLM judge), and pytest test cases organized by skill. Each test sends source content through a skill via the harness, captures the output, and runs assertions against it. Deterministic checks handle hard rules (regex, string matching); the LLM judge handles semantic checks that regex can't cover.

## Components

### Harness — `tests/support/harness/`

Generic Claude Code test runner. Invokes `claude -p` as a subprocess.

- `tests/support/harness/__init__.py`
- `tests/support/harness/claude_runner.py` — `ClaudeRunner` class

```python
class ClaudeRunner:
    def __init__(
        self,
        model: str = "haiku",
        timeout: int = 30,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ):
        self.model = model
        self.timeout = timeout
        self.run_id = uuid.uuid4().hex[:8]
        self.cwd = Path(cwd) if cwd else self._default_cwd()
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.env = {**os.environ, **(env or {})}

    def _default_cwd(self) -> Path:
        if env_cwd := os.environ.get("CLAUDE_TEST_CWD"):
            return Path(env_cwd)
        project_root = Path(__file__).parents[3]
        return project_root / "tmp" / "tests" / self.run_id

    def run(self, prompt: str) -> str:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", self.model, "--output-format", "text"],
            capture_output=True, text=True, timeout=self.timeout,
            cwd=self.cwd, env=self.env,
        )
        return result.stdout.strip()
```

**Config hierarchy:** explicit kwargs > env vars (`CLAUDE_TEST_CWD`, `CLAUDE_TEST_MODEL`, `CLAUDE_TEST_TIMEOUT`) > defaults.

**Default cwd:** `tmp/tests/<run_id>` — gitignored, isolated per session. `run_id` stored on the instance for logging/debugging.

### Assertions — `tests/support/assertions/`

Two assertion types: deterministic (pure Python) and LLM judge (via harness).

- `tests/support/assertions/__init__.py`
- `tests/support/assertions/deterministic.py`
- `tests/support/assertions/judge.py`

#### Deterministic Assertions

| Function | What it checks | Returns |
|----------|---------------|---------|
| `no_em_dashes(text)` | `—` not present | `list[str]` — lines containing em dashes (empty = pass) |
| `long_sentences(text, max_words=25)` | sentence word count | `list[str]` — offending sentences |
| `banned_words(text)` | word blocklist | `list[str]` — found banned words |
| `urls_preserved(source, output)` | URLs from source appear in output | `list[str]` — missing URLs |
| `stats_preserved(source, output)` | numbers/stats from source in output | `list[str]` — missing stats |
| `email_signoff(text)` | ends with "- Swift" or "Happy Hacking,\nSwift" | `bool` |
| `slack_word_count(text)` | total word count | `int` |
| `linkedin_hashtag_count(text)` | hashtag count | `int` |

**Banned word list:** "synergy", "leverage" (as verb), "ecosystem", "paradigm shift", "game-changer", "delve", "excited to share".

#### LLM Judge

```python
@dataclass
class JudgeResult:
    passed: bool
    checks: dict[str, bool]      # criterion_name -> pass/fail
    reasoning: dict[str, str]    # criterion_name -> explanation

def judge(source: str, output: str, rubric: str, runner: ClaudeRunner) -> JudgeResult:
    """Send a structured rubric prompt through the harness, parse JSON result."""
```

Used sparingly for semantic checks:
- "Opening sentence contains the main point/ask"
- "Reads as a rewrite of the source, not original content"

### Test Cases — `tests/skills/ghostwrite/`

- `tests/skills/ghostwrite/conftest.py` — ghostwrite-specific fixtures (test inputs per medium)
- `tests/skills/ghostwrite/test_ghostwrite_rules.py` — general compliance + content preservation (~6 tests)
- `tests/skills/ghostwrite/test_ghostwrite_mediums.py` — medium-specific formatting (~10 tests)

#### `test_ghostwrite_rules.py` (~6 tests)

| Test | Assertions |
|------|------------|
| No em dashes in email rewrite | `no_em_dashes` |
| Sentences stay under 25 words | `long_sentences` |
| No banned words in output | `banned_words` |
| No AI tells (excited to share, leverage, delve) | `banned_words` |
| URLs from source preserved verbatim | `urls_preserved` |
| Stats/numbers from source preserved | `stats_preserved` |

#### `test_ghostwrite_mediums.py` (~10 tests)

| Test | Medium | Assertions |
|------|--------|------------|
| Email has valid sign-off | email | `email_signoff` |
| Email greeting format | email | regex for "Hey, [Name] --" |
| Email opens with the point | email | `judge` (main point first) |
| LinkedIn word count 100-200 | linkedin | word count check |
| LinkedIn has 4-7 hashtags | linkedin | `linkedin_hashtag_count` |
| LinkedIn hooks first | linkedin | `judge` (no "I'm excited to share") |
| Slack under 60 words | slack | `slack_word_count` |
| Slack is chat prose (no bullets/bold) | slack | regex for `*`, `-` at line start |
| Slack ask/request first sentence | slack | `judge` (ask first) |
| Blog has section headers | blog | regex for markdown headers |

### Shared Fixtures — `tests/conftest.py`

```python
@pytest.fixture(scope="session")
def runner():
    return ClaudeRunner(
        model=os.environ.get("CLAUDE_TEST_MODEL", "haiku"),
        timeout=int(os.environ.get("CLAUDE_TEST_TIMEOUT", "30")),
    )
```

Session-scoped — shared across all tests (no state between calls, each `run()` is a fresh subprocess).

### Infrastructure Changes

**`pyproject.toml`:**
- Add `pytest` to dev dependencies
- Add pytest config:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: tests that make multiple LLM calls"]
```

**`Makefile`:**
- Add `test` target: `uv run pytest tests/ -v`

## Data / Interfaces

### Test Input Shape

Each test case provides:
- **Source content** — the raw text to rewrite (inline in fixtures or conftest)
- **Medium** — email, linkedin, slack, or blog
- **Prompt** — a natural-language instruction that triggers ghostwrite (e.g., "Rewrite this as a Slack message: {source}")

### Output

The harness returns a single string — the ghostwrite output. All assertions operate on this string (plus the original source for preservation checks).

## Documentation

### `docs/evals.md`

The testing guide. Already referenced in CLAUDE.md but does not exist yet. Covers:

- How to run the suite (`make test`)
- How to write a new test (file structure, naming, fixtures)
- How to add a deterministic assertion
- How to use the LLM judge
- Environment configuration (env vars for model, timeout, cwd)
- How to add tests for a new skill

### Inline Docstrings

All public APIs get docstrings:
- `ClaudeRunner` class and `run()` method
- Each deterministic assertion function (parameters, return value, what constitutes a pass)
- `judge()` function and `JudgeResult` dataclass

## Testing

- Run: `make test`
- Expected: ~16 tests, all passing with haiku
- Each test makes one `claude -p` call (plus one more for judge-based tests)
- Target runtime: under 2 minutes for the full suite

## Open Questions

None — design is fully specified for the initial ghostwrite scope.
