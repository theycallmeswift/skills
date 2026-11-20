# Synthesis brief

<!-- Fill the <...> slots, then hand this whole file to the synthesizer. -->

You are synthesizing a multi-model design critique into a short, verified list of changes for the design's owner. Several vision models each critiqued the same design twice against the same rubric. Their replies disagree, overlap and contain false claims: expect 8–12 per pass, mostly "passing" colours that fail WCAG and misread screenshots. Your job is to keep what is true and important, drop what isn't, and show your checks. The owner decides what to apply, so a confident wrong recommendation costs more than a missed minor one.

## Inputs

- Rubric: `<OUT>/rubric.md`. Its "Settled decisions" are fixed; its open questions need answers.
- Records: `<OUT>/records/*.json`, one per model run: `model`, `run`, `ok`, `error`, `raw_text`, `parsed` (the reply JSON, or null), `cost_usd`, `seconds`.
- Run stats: `<OUT>/run_stats.json`.
- Package: `<OUT>/package/`: the gridded screenshots (columns A–H, rows 1–8), `manifest.json` (file, frame, theme, description) and the tokens file.
- Contrast script: `python3 <path to scripts/contrast.py> FG BG [FG BG ...]` prints the WCAG 2.2 ratio and AA/AAA pass or fail for each pair.
- Write your output to `<OUT>/synthesis.md`.

## Method

1. **Collect.** Read every record. Where `parsed` is null but `raw_text` holds findings (invalid JSON, prose around the JSON), extract the issues by hand and mark them hand-extracted; those runs count as usable. A run with no usable text is unusable: list it in run stats.
2. **Cluster** issues by element and problem: the same element with the same problem is one change, however it was worded or whichever cell it cites.
3. **Rank** clusters by the number of distinct models raising them (a model's two runs count once), then severity (the majority among those models, ties go up), then confidence. Write the count as n/N, where N is the number of models with at least one usable run.
4. **Flag same-vendor agreement.** A vendor is the part of the slug before `/`. If every model behind a cluster shares a vendor, mark it "same vendor only": that is one taste, not independent agreement.
5. **Recompute every contrast claim** with the contrast script, using the hex values from the tokens file, never colours sampled from screenshots. Recompute each proposed fix colour too. A claim whose ratio is wrong, or a fix colour that fails AA for its role, is a false claim: reject it with the recomputed number, or keep the problem and replace the fix with a passing value you computed.
6. **Check every visual claim against the screenshots.** Open the cited frame and cell. If the element isn't there, looks different, or the claim misreads it, reject it as a misread.
7. **Drop, with a reason each:**
   - false claims (wrong ratio, misread screenshot), with the recomputed or observed fact;
   - page artifacts: critiques of the grid lines, margin labels, captions, or review annotations ("Recommended", arrows, callouts) rather than the design;
   - settled-decision conflicts: anything that reverses, softens or reopens a decision in the rubric's settled list, however many models agree. Cite the decision.
8. **Split** what survives: changes raised by two or more models go in the ranked list; single-model ideas go under Consider.
9. **Answer** each of the rubric's open questions: the consensus, then any dissent with model names.

## Output

Write `synthesis.md` in exactly this shape:

```markdown
# Synthesis: <pass>, <date>

## Summary

- <five bullets: the most important findings and what they mean for the owner>

## Ranked changes

| # | Change | Models | Severity | Effort |
|---|---|---|---|---|
| 1 | <change with the exact fix> | 3/5 (<model>, <model>, <model>) | high | S |

Effort: S = a token or one-line change; M = one component; L = layout or structure. Mark same-vendor-only rows.

## Changes

### 1. <change>

- **Problem:** <what is wrong, frame and cell>
- **Why it matters:** <for who the work serves>
- **Fix:** <exact hex, px or token>
- **Verified:** <the check you ran and its result, e.g. "contrast.py #8A8F98 #2A2D35 → 4.24:1, fails AA normal; fix #9BA1AB → 5.30:1 passes" or "frame Dashboard 1/2, C4: label truncated as claimed">

## Consider

- <single-model idea, exact fix> (<model>)

## Answers

- **<question>:** <consensus; dissent with model names>

## Rejected

| Claim | Models | Reason |
|---|---|---|
| <claim as made> | <model>, <model> | False: <recomputed ratio or observed fact> |
| <claim> | <model> | Page artifact: <what it critiqued> |
| <claim> | <model>, <model> | Settled decision: "<decision>" |

## Run stats

- Cost $<total>, <seconds> s; <raw issue count> issues raised, <cluster count> after clustering.
- Parsed <X>/<Y> runs. Hand-extracted: <model#run, or none>. Unusable: <model#run: reason, or none>.
```

Keep the recomputed numbers in the Verified and Rejected lines exactly as the script printed them.
