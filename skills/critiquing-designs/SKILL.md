---
name: critiquing-designs
description: "Use when the user wants a design, mockups, UI screenshots or a design system critiqued by several AI models, or wants other models' opinions on visual design, including turning a finished multi-model critique (its run records) into what to change. Covers asks like \"have a few models critique these mockups\", \"run a multi-model design review\", \"run a design-system critique across models\", \"get GPT and Gemini to grade this dashboard\", \"do an aesthetic pass on the dashboard against reference sites\", \"the model critique finished, what should we change?\". Use it whenever more than one model should judge a design, even if the user names no models. Runs vision models through OpenRouter and needs OPENROUTER_API_KEY. Don't use for a quick opinion from the current model on a screenshot, code review of UI components, automated accessibility audits, or building a design system (building-design-systems)."
---

# Critiquing designs

Get a design critiqued by several vision models, then turn their replies into a short list of verified changes the user approves. One model's critique is one model's taste, stated with confidence; several models fix that only if their claims are checked. Expect 8–12 false claims per pass, mostly "passing" colours that fail WCAG and misread screenshots.

Success: every applied change was approved by the user, survived verification, and contradicts no decision the user already made. Agents usually get the model calls right and miss the rest; steps 2, 6 and 7 carry the weight.

| Step | Writes | Stop the line when |
|---|---|---|
| 1. Calibrate taste (optional) | Picked REF images | The user hasn't picked |
| 2. Draft the rubric | `rubric.md` | The user hasn't approved the rubric |
| 3. Package | `package/` | A screenshot is missing or unreadable |
| 4. Models and cost | `models.txt` | The user hasn't approved models, estimate and cap |
| 5. Run | `records/`, `run_stats.json` | Spend reaches the cap or the balance |
| 6. Synthesize | `synthesis.md` | A spot-check fails: send it back |
| 7. Check prior decisions | Conflicts moved to Rejected or Decide | — |
| 8. Decision page | `decisions.md` | The user hasn't approved rows |
| 9. Apply | The design files | A changed token pair fails contrast |

## Workspace root

Paths are relative to the workspace root:

- Interactive session: the current project directory.
- Eval or scripted invocation: the root the prompt names; honor `PROJECT_ROOT` in the env for any script invocation.

The skill's files live under `skills/critiquing-designs/`; run its scripts with `python3` from the workspace root.

## Prerequisites

- Each pass gets its own out dir in a git-ignored scratch area, e.g. `tmp/critique/<YYYY-MM-DD>-<slug>-<pass>/` (`OUT` below). If the project doesn't ignore `tmp/`, pick a dir it does ignore.
- `run_critique.py` reads `OPENROUTER_API_KEY` from the environment. If it's unset, ask the user to set it; never ask them to paste it into chat.
- `grid.py` and `contact_sheet.py` need Pillow. If either exits 2 asking for it, install it (`pip install pillow`) and rerun.

## Passes

Pick the passes the ask needs, each with its own rubric template in `assets/`:

- **Design system** (`skills/critiquing-designs/assets/rubric-design-system.md`): tokens, scales, contrast, component states.
- **Page** (`skills/critiquing-designs/assets/rubric-page.md`): one screen or flow doing its job. When it grades brand fit against the design system, run the design-system pass first and feed its applied results in.
- **Aesthetic** (`skills/critiquing-designs/assets/rubric-aesthetic.md`): look and feel against REF images the user picked. Run it separately: correctness findings crowd out taste when both share a rubric.

## 1. Calibrate taste (optional)

Before an aesthetic pass with no reference sites named, read [taste-calibration.md](references/taste-calibration.md) and follow it. The user's picks become the REF images for the aesthetic package.

## 2. Draft the rubric

Copy the pass's template to `OUT/rubric.md` and fill every `<...>` slot:

- **Who the work serves:** the users, their context, the job the screen does.
- **Settled decisions:** every design decision the user has made, in this session and in the repo (design docs, specs, decision logs, comments in the design-system source). Models argue with anything not listed, and step 7 reuses this list.
- **Criteria and weights:** keep the template's unless the user's goal shifts them.
- **Open questions:** the questions the user actually wants answered.

Keep the template's issue rules, page-artifact warning and JSON reply schema unchanged: the runner and synthesis depend on them.

**Stop: show the rubric and get the user's approval before any spend.** The rubric decides what every paid call looks for; a wrong one wastes the whole run.

## 3. Package

Build `OUT/package/` with the gridded screenshots, the design system as text, and a manifest:

```
python3 skills/critiquing-designs/scripts/grid.py <screenshot> [<screenshot> ...] --out-dir OUT/package
```

`grid.py` resizes to fit 1280px wide, splits into parts that fit 2000px tall (the 24px grid margin is inside both limits), and adds an A–H × 1–8 margin grid so models can cite cells like `C4`. It prints the output paths (`<stem>.png`, or `<stem>-part1.png`, `-part2.png`, ...). Inputs need distinct file names (stems); a duplicate exits 2.

- Add the design system as one text file, e.g. `OUT/package/tokens.md` with every token's name and hex or px value. Tokens belong in text: models misread colours from pixels.
- Aesthetic pass: add the REF images (gridding optional) with frames `REF1`, `REF2`, ...
- Write `OUT/package/manifest.json`, one entry per image, in reading order, naming the files `grid.py` printed:

```json
[{"file": "dashboard-part1.png", "frame": "Dashboard 1/2", "theme": "dark", "description": "Overview: header, KPI row, activity table"}]
```

Every other `.md`, `.txt` or `.json` file in the package is sent as text, so keep stray files out.

## 4. Pick models and estimate cost

Pick 4–6 vision models (image input) from the top of OpenRouter's Design Arena ranking, one per vendor: agreement means something only when the models don't share training. Write their slugs one per line to `OUT/models.txt`. Propose a cap a little above the likely estimate, then run the estimate. It makes no completion call:

```
python3 skills/critiquing-designs/scripts/run_critique.py OUT/rubric.md OUT/package OUT --models OUT/models.txt --runs 2 --cap <usd> --estimate-only
```

It prints the models, `estimate`, `cap` and `balance` (credits left on the key), sized from the package contents. Exit 2 names an unknown slug or a model with null or negative pricing (such as `openrouter/auto`); replace it and rerun. Exit 3: the estimate is over the cap or balance.

**Stop: show the models, estimate, cap and balance, and get approval before running.** The key may be shared and the spend is real. Never run past the cap or the balance: if the estimate exceeds either, cut models or runs, or ask the user to raise the cap or top up.

## 5. Run

```
python3 skills/critiquing-designs/scripts/run_critique.py OUT/rubric.md OUT/package OUT --models OUT/models.txt --runs 2 --cap <usd>
```

Two runs per model, in parallel. It rechecks the cost gate (exit 3 if over the cap or balance; nothing spent), reserves each call's estimate before sending it (a call that would pass the cap or balance is skipped and recorded), writes one record per model run to `OUT/records/` as each finishes, writes `OUT/run_stats.json`, and prints `parsed X/Y runs, $cost, Ns`. A `records/` dir that already holds records is refused (exit 2) unless you pass `--only` or `--force` (overwrite all). Some models take 10+ minutes per call; let it finish.

Exit 1 means some runs failed or returned no parseable JSON; the records are still written.

- **Parsed null with `raw_text`:** don't rerun. Synthesis extracts its findings by hand.
- **Failed (timeout, connection, 408, 429, 5xx; each already retried once):** rerun just those with `--only <slug>#<run>,...`, passing `--cap` as the approved cap minus the spend so far (`total_cost_usd` in `run_stats.json`, summed over every earlier invocation). A rerun spends against the same approval.
- **402 (insufficient credits):** stop. Tell the user what ran and what didn't; continue only on what they decide.

## 6. Synthesize

Hand synthesis to a fresh subagent if available, else do it yourself in a separate pass: a fresh reader checks claims instead of confirming what the rubric author expected. Brief it with `skills/critiquing-designs/assets/synthesis-prompt.md`, its slots filled with the paths to `OUT/` and `skills/critiquing-designs/scripts/contrast.py`. It writes `OUT/synthesis.md`.

Spot-check before trusting it: rerun `contrast.py` on two of its contrast numbers and open the screenshot cell behind one visual claim. If either is wrong, send it back with the error.

## 7. Check prior decisions

Check every surviving recommendation against every decision the user made in this session and in the repo, not just the rubric's list: decisions made after the rubric was written, or missed when it was, count too. Search the repo for them now (decision logs, design docs, ADRs, specs, comments in the design-system source).

- **Prior decisions win, even when every model agrees.** Unanimity among models is not new information the user lacked.
- A recommendation that reverses or erodes a decision is never recommended. Drop it to Rejected, citing the decision.
- If the models give evidence the user may not have seen (a failed WCAG ratio, a concrete harm to who the work serves), raise it as a **Decide** row instead: the decision, the evidence, the options, listed neutrally. Don't lean toward reversing the decision or a partial version of it; the user already weighed that. Never apply or drop it silently.

## 8. Decision page

Write `OUT/decisions.md`:

1. **Recommendations table first:**

   | # | Change | Models | Severity | Effort | Call |
   |---|---|---|---|---|---|
   | 1 | `--text-muted` #8A8F98 → #9BA1AB (4.24:1 → 5.30:1 on `--surface-raised` #2A2D35) | 4/5 (names) | high | S | Recommend |
   | 2 | Restore text badges in matrix cells | 5/5 (names) | medium | S | Decide: conflicts with "badges removed" (this session). A) keep removed; B) restore |

2. **The full ranked list** from `synthesis.md`, with problem, fix and the check that verified each.
3. **Rejected**, with each reason and recomputed number.

Post the recommendations table in chat and ask one question: which rows to apply (e.g. "1–6, 9", "all Recommend rows", or changes).

**Stop: wait for approval.** The user owns the design; the models only advise.

## 9. Apply

Apply only the approved rows, exactly as approved. Then recompute contrast for every foreground/background pair that uses a changed token:

```
python3 skills/critiquing-designs/scripts/contrast.py <fg> <bg> [<fg> <bg> ...]
```

If a pair fails AA, report it with the nearest passing value as a new row to approve; don't adjust it silently. Approved changes become settled decisions for any later pass. Report: rows applied, contrast results, rows skipped, and total spend.

## Gotchas

- **Proposed fix colours fail WCAG too:** recompute them.
- **Models critique page artifacts:** grid lines, margin labels, captions and review notes like "Recommended". The rubric tells them not to; synthesis drops what slips through.
- **A shared key can run dry mid-run.** The cap and `--only` reruns keep the spend bounded.
- **Reasoning models can return empty replies** when hidden reasoning eats `max_tokens`. The runner sets 32000 and retries once; an empty record after that is a failed run, not a clean bill of health.
