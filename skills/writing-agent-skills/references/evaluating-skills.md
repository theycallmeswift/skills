# Evaluating skills

Procedural how-to for the RED → GREEN → REFACTOR workflow. Self-contained — does not assume any project-level conventions doc exists.

## Why eval-first

A skill without evals is a guess: you don't know whether the agent reads it as intended, whether the content earns its place, or whether iteration is improving or regressing the skill.

Build the eval before the skill. Run without the skill to establish a baseline, then write the minimum to beat it. Skills built this way solve real gaps; skills built without evals document imagined ones.

## Two eval types

**Output evals** measure the quality of what the skill produces. The same prompt runs across two arms declared in `pyproject.toml` — a `baseline` that runs the agent bare and a `trial` that runs it with the plugin loaded; the set's `baseline = "baseline"` key makes the delta (trial − baseline) the quality metric.

**Routing evals** measure whether the description fires the skill at all. At most 10 queries covering both polarities, each an ordinary eval whose assertions are activation lines — one per skill that has a stake in the ask — in the same set.

Author both. Output evals don't matter if the skill never loads.

## Eval directory shape

Skills ship clean; their evals live beside them under a root `evals/` tree:

```
skills/your-skill/
└── SKILL.md                    # plus references/, assets/, scripts/ — nothing eval-related
evals/your-skill/
├── <scenario>/
│   ├── eval.md                 # one self-contained output eval (eval id == folder name)
│   └── workspace/              # starting files for that eval (optional)
├── triggers/                   # asks that must reach this skill, one file per query
│   └── <query-slug>.eval.md
└── not-triggers/               # near-misses no loaded skill owns
    └── <query-slug>.eval.md
```

The runner discovers any `eval.md` or `<stem>.eval.md` beneath `evals/`; the filename is the marker. Case identity is `(group, eval_id)`, both kebab-case — the folder name and the file stem — so a routing query lives in exactly one file across the repo — under the skill it should reach — and a sibling that shares the vocabulary adds its own `not invoked` line there rather than a duplicate file. No install script is needed: the `trial` arm loads the whole plugin from the staged repo with `--plugin-dir /project`, and `baseline` runs bare. (benchspec does run a `setup.sh` from the eval folder when one exists, with `BENCHSPEC_ARM` set, for suites that install per arm; this plugin has none.)

`eval.md`: YAML frontmatter (the `---`/`---` delimiters are required even when empty; `history:` is the **only** allowed key — a list of prior `{role, content}` turns rendered as a transcript prefix, e.g. an assistant proposal the `## Prompt` then approves), then a required `## Prompt` and a required `## Assertions` checklist. The `## Prompt` is the single graded turn. One assertion per `- [ ] …` line, except a line with indented `- [ ]` children is a display-only header (never graded) whose children flatten to one assertion each — one nesting level only, and `###` subheadings under Assertions are likewise display-only groups. Anything else — unknown headings, prose before the first `##`, plain `-` bullets, other frontmatter keys — fails at collection with the path quoted.

Write every path in the eval `./`-relative (`./notes/standup.md`), because that is how the agent, the checkers, and the judge all see the workspace. `{TODAY}` is the one placeholder; any other `{UPPERCASE}` token is rejected.

Assertion typing — every assertion is plain prose; the **binder** classifies each line at grade time:
- When confident, it maps the prose to one deterministic checker — `file_exists` / `not_file_exists`, `glob_count`, `regex`, `frontmatter_has`, `sha256_match`, `skill_invoked` / `not_skill_invoked` — run on the host for zero judge cost. Persistence and negation claims other than those two negated forms ("still present", "not duplicated") always punt.
- Otherwise it punts the line to the LLM judge.
- Keep a deterministic claim atomic (one fact per line, no `and`) if you want the binder to bind it rather than punt. `` Skill `X` invoked `` and `` Skill `X` not invoked `` are exact by convention; give each a `- if: {BENCHSPEC_ARM} != "baseline"` sub-bullet so it is graded off the baseline, where the skill can't fire (`make evals:lint` flags a missing one). There is no checker syntax to author — the split is invisible from the suite.

**Arms are declared in `pyproject.toml`, not implied by the runner.** `[tool.benchspec.sets.default]` is the one eval set: its `arms` are the report columns (`harness`/`model`/`effort`/`env`/`harness_args` *inherit* from set-level defaults unless the arm overrides them), and the set-level `baseline` key names the arm every Δ is measured against. Here `baseline` is bare and `trial` carries `harness_args = ["--plugin-dir", "/project"]`, both on the set's `model`. (`--benchspec-model haiku` overrides the *set's* `model` for every inheriting arm, so both run at haiku and the trial still yields a real Δ.)

The runner validates at collection, so the plan preview doubles as a schema check:

```
make evals SKILL=<skill> EVAL_ARGS="--collect-only -q"
```

Any unknown field or shape mismatch is a hard error. `make evals:lint` is free and static: it flags wording the judge cannot fairly grade — vague adverbs (`properly`, `gracefully`), paths without a `./` anchor, relative claims (`better`) with no comparand. `uv run --group evals benchspec analyze` asks the binder itself which lines bind and which punt (it needs `GEMINI_API_KEY` and always exits 0), so you can tighten wording until the facts you care most about grade deterministically.

## Workspace layout for runs

Ephemeral, gitignored. Lives under `tmp/`:

```
tmp/evals/
├── iteration_01/
│   ├── meta.json, index.jsonl, benchmark.json, benchmark.md
│   └── skills/                  # fixed name, whatever the search path
│       └── <group>/
│           └── eval-<eval_id>/
│               ├── trial/           # one dir per arm name
│               │   └── sample-0/    grading.json, timing.json, transcript.json, provenance.json, session.jsonl
│               └── baseline/
│                   └── sample-0/
└── iteration_02/
```

Single-sample runs (the default) still shard under `sample-0/`; `--count N` adds `sample-1/` and up. See [`running-evals.md`](running-evals.md) for per-sample aggregation in `benchmark.{json,md}`.

Don't scaffold upfront — the runner creates directories as runs complete. Iteration numbers auto-increment; each run appends, never overwrites.

## Picking eval scenarios

Three scenarios minimum:

1. **Happy path** — the case the skill is designed for, clean inputs.
2. **Edge case** — ambiguous input, partial info, decoy.
3. **Failure mode** — missing inputs, contradictions, the case the skill must handle *gracefully*.

A skill with only happy-path evals will pass its tests and surprise its users.

## Writing assertions

Plain-English sentences, not regex. One sentence per assertion. A non-engineer should be able to read it and understand what passing means.

**Every assertion must be discriminating.** Ask: *"could a clearly wrong output satisfy this?"* If yes, tighten until the answer is no.

| Weak | Strong |
|---|---|
| `./output.docx exists` | `./output.docx contains a heading with the customer's name and the invoice date` |
| `the response is helpful` | `the response cites at least one specific line from the input diff and names the failure mode` |
| `the prompt has a role` | `the role is a single sentence naming who the model is acting as and its top constraint` |

For subjective outputs (style, design, judgment), evals work poorly — prefer qualitative review instead. Mixed-grading is fine: mechanical structural assertions for what's checkable, human review for the rest.

## RED — capture baselines

**Gate: do not draft SKILL.md until baselines are captured.** Drafting from imagined problems addresses imagined gaps.

Run `make evals SKILL=<skill> EVAL_ARGS="-k baseline"` (the `baseline` arm is the bare-agent clean room). It handles clean-room isolation (a fresh agent in a microVM whose working directory holds only the eval's `workspace/`; the repo is mounted read-only at `/project` on every arm, but nothing loads it as a plugin on baseline), grading, and workspace layout. See [`running-evals.md`](running-evals.md).

Read the transcripts: for discipline-enforcing skills, verbatim rationalizations are the skill's actual content; for technique skills, structural misses are what the skill needs to fix.

## GREEN — run the trial arm and grade

Run `make evals SKILL=<skill>` (both arms by default). It runs the trial arm (the plugin loaded inside an isolated microVM, not a subagent), grades both arms with the binder plus an LLM judge fed deterministic facts, and writes grading and benchmark files.

For output evals on a weaker model *with the baseline/trial contrast preserved*, pass `EVAL_ARGS="--benchspec-model haiku"`: it overrides the set's `model` default so both arms run at haiku and the Δ is real. (The plural `--benchspec-models` is a sweep that replaces the declared arms with one per value — it drops the baseline/trial contrast and is only for explicit sweep runs.)

## REFACTOR — iterate until the signal flattens

Read transcripts, not just outputs. Common moves:

- Instructions sending the agent down an unproductive path → delete.
- Three runs all writing the same helper script → bundle it in `scripts/`.
- Repeated MUSTs that aren't holding → replace with the *reason*. Modern models follow why-explanations more reliably than capitalized imperatives.
- Specific fixes for specific failures → try a more general framing first; specific MUSTs overfit.

Snapshot the skill before editing (`cp -r your-skill tmp/skill-snapshots/your-skill/`) so the next iteration's baseline points at the old version.

Stop when the user is satisfied, the delta flattens, or you can't think of an improvement that isn't speculative.

## Routing evals

Output evals test what happens *after* the skill loads. The `description:` field decides whether it loads at all.

Build at most 10 queries; fewer is fine. Every query needs a distinct reason to exist: a phrasing or intent the description must catch, or a near-miss negative that shares keywords with the skill but needs something different. If two queries would fail for the same reason, keep one. Rewordings of one intent ("write this up as a spec", "turn this into a spec", "draft a spec") are one query, not five. Cover both polarities, weighted toward near-miss negatives; obviously unrelated negatives ("fix this TypeError" for a prompt-writing skill) prove nothing.

**What counts toward the 10:** the files in the skill's own `triggers/` and `not-triggers/` folders. An activation line the skill adds to a sibling's file doesn't count against the cap but does count as coverage, so a skill whose negatives all live as lines on its siblings' queries still covers both polarities. That line has to be a real near-miss too, not a free extra assertion. Substantive queries only — trivial one-step asks don't trigger skills regardless of description quality.

Each query is one file — `evals/<skill>/triggers/<query-slug>.eval.md` for an ask that must reach this skill, `evals/<skill>/not-triggers/<query-slug>.eval.md` for a near-miss no loaded skill owns — with the verbatim user message as the `## Prompt` (routing-sensitive; never reword) and one activation line per skill that has a stake in it: `` Skill `<skill>` invoked `` for the owner, `` Skill `<other>` not invoked `` for a sibling that shares the vocabulary. Leave the sibling line out when the owner may legitimately delegate to that sibling mid-task, since activation counts any dispatch in the run. A positive that presupposes a prior design discussion ("write up what we landed on") gets a short `history:` recap so the ask refers to something; in an empty session the agent correctly says there is nothing to write up instead of routing. They run in the same set as the output evals, so on `trial` the skill competes with its real peers; the arm clause keeps them off `baseline`.

Run: `make evals SKILL=<skill>` (or `-k` the query slugs). See [`running-evals.md`](running-evals.md). A query that routes on opus but not on a weaker tier is a model-tier boundary to note alongside the skill, not a description defect to chase with more trigger phrases.

## Analyst pass

Read the benchmark critically:

- **Assertions that pass regardless of skill** — not discriminating; rewrite or drop.
- **High run-to-run variance** — flaky scenario, weak assertion, or genuine instability.
- **Time/token deltas pointing the wrong way** — quality up, cost up disproportionately; flag the tradeoff.

Aggregate pass rates hide things worth knowing. Author or analyst subagent, after the benchmark — not as part of grading.
