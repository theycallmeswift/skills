# google-slides — eval record

Recorded 2026-10-24 from `iteration_03`: benchspec 0.0.5, Docker sandbox, Claude Code 2.1.310 in the guest, sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=google-slides EVAL_ARGS='--count 3 -n 4'` (output and routing together, 78 cells, about 20 minutes). Activation lines (`Skill … invoked`) are scoped off baseline and excluded from these tallies. The previous record, `redesigning-google-slides` at `iteration_01` on 2026-10-23, is quoted in the last column for the four scenarios carried over.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ | trial on 2026-10-23 |
|---|---|---|---|---|
| changed-fact-sweep | 12/24 (50%) | 22/24 (92%) | +42pp | 22/24 (92%) |
| missing-workspace-asks-first | 3/15 (20%) | 15/15 (100%) | +80pp | 15/15 (100%) |
| new-section-matches-deck | 13/18 (72%) | 16/18 (89%) | +17pp | 18/18 (100%) |
| shared-deck-asks-first | 0/12 (0%) | 11/12 (92%) | +92pp | 9/12 (75%) |
| new-deck-from-template | 33/33 (100%) | 32/33 (97%) | −3pp | — |
| new-deck-no-template | 18/18 (100%) | 18/18 (100%) | 0pp | — |
| new-section-from-content | 20/30 (67%) | 30/30 (100%) | +33pp | — |
| **Headline** (mean of per-sample rates) | **58%** | **96%** | **+37pp** (noise band ±2pp) | |

Per sample, the trial took 58 s and 475k tokens against the baseline's 53 s and 415k.

## 2026-10-26: measure the reference, quality critic

Two runs after the skill added the reference measurements, density and image rules, the prototype checkpoint and the quality critic. benchspec 0.0.5, Docker sandbox, sonnet.

`iteration_01`, the full suite on the new skill at `--count 1` (28 cells, 63 minutes serial):

| Eval | baseline | trial | trial at `iteration_03` |
|---|---|---|---|
| new-slides-illustrated-deck (new) | 33% | 89% | — |
| changed-fact-sweep | 62% | 88% | 92% |
| missing-workspace-asks-first | 20% | 100% | 100% |
| new-deck-from-template | 100% | 100% | 97% |
| new-deck-no-template | 100% | 100% | 100% |
| new-section-from-content | 70% | 90% | 100% |
| new-section-matches-deck | 100% | 100% | 89% |
| shared-deck-asks-first | 0% | 100% | 92% |
| **Headline** | **61%** | **96%** | **96%** |

One sample per cell, so no noise band; no scenario moved outside what the 3-sample record already shows run to run. Routing cells passed (6/6 scoped assertions on the trial arm). Per sample, the trial took 208 s and 1.26M tokens against the baseline's 191 s and 1.44M. The guest ran Claude Code 2.1.282, older than the 2.1.310 of `iteration_03`.

`iteration_02`, the red run: `new-slides-illustrated-deck` with the previous SKILL.md (from `main`) at `--count 3 -n 6`. Baseline 11/27 (41%, ±6%), trial 8/18 (44%, ±0%), +4pp within the ±4pp noise band: the old skill scores what no skill scores, against 89% for the new one. One trial cell failed before the agent started (Docker couldn't mount the project dir under `-n 6`), so the trial figure is two samples. Claude Code 2.1.310 in the guest.

## Routing evals — trial arm: 18/18

| Query | Expected | Result |
|---|---|---|
| eval-numbers-changed | google-slides invoked | 3/3 |
| new-deck-from-scratch | google-slides invoked | 3/3 |
| these-last-slides-are-bullets | google-slides invoked | 3/3 |
| export-deck-pdf | google-slides not invoked | 3/3 |
| pptx-restyle | google-slides not invoked | 3/3 |
| summarize-deck | google-slides not invoked | 3/3 |

## Notes

**The new-deck path doesn't beat the baseline.** With the `google-workspace` stand-in installed, every baseline sample copied the named template with Drive, built on its layouts, cleared its sample slides, kept the user's wording, and re-read the deck afterwards (33/33). Without a template, every baseline sample built a stock-theme deck with no invented colors or logo (18/18). The trial passes the same checks by a different route on `new-deck-no-template`: all three samples asked once for a template, with the slide plan attached, and offered the stock theme as the fallback. The trial's one miss on `new-deck-from-template` was a judge call on whether `s01_slide` names a role. The skill's new-deck text was cut to the rules the issue asks for (copy, never edit the template, ask once, stock theme with one accent and two layouts) after this run; `iteration_04` re-ran the two new-deck scenarios on the trial arm with the cut text and scored the same: 32/33 and 18/18.

**What the skill fixes on existing decks.**
- **Adding slides sweeps the deck.** Asked to add a sixth step, Automate, after slide 8, no baseline sample updated or proposed wording for "five steps" on slides 1 and 3, and none added "6 Automate" to the step tracker on slides 4–8. One deleted two of the three new slides while fighting a layout. Two built both new list slides identically. Every trial sample duplicated a step slide for the new step, gave the two list slides different layouts, and either updated the counts and trackers or listed them with wording.
- **Stale copies of a changed fact, live edits without `google-workspace`, someone else's deck:** the same pattern as on 2026-10-23. The baseline renamed the stat but left the tracker, edited straight away without the skill, and edited Priya's deck when told to "go ahead". The trial swept, asked first, and stopped on Priya's ownership in all three samples.

**Fixed between runs.** In `iteration_02`, two trial samples on `new-section-from-content` stopped to ask because the owner, `owner@example.com`, couldn't be matched to the user. The ownership line now stops only when the user has said who they are and the owner differs, or the deck is widely shared. It also asks when the metadata can't be read after fixing the call: one `shared-deck-asks-first` sample had called `get_file_metadata` with `presentationId`, got an error, and edited anyway. With that change, `shared-deck-asks-first` rose from 75% to 92%.

**Remaining misses.**
- `new-section-matches-deck`, 16/18. One sample named shapes `s09_row1_bg` (row index before role), and one used tip-badge colors outside the deck's palette. On 2026-10-23 it scored 18/18. The baseline dropped too (89% → 72%), so the scenario is noisier than one run shows.
- `changed-fact-sweep`, 22/24. One sample didn't mention slide 7's speaker notes. One rewrote slide 7's title to "Approve in 4 minutes" and said so, which the judge failed on "names the title as wrong" (the same inconsistent grading as on 2026-10-23).
- `shared-deck-asks-first`, 11/12. One sample stopped correctly but described the redesign only in general terms.

**The critic still never runs.** The fake serves only recorded thumbnails, so edited and new slides have no render. Trial samples fell back to geometry reads and said they couldn't see the result.

**Fake.** The Slides and Drive tools come from `evals/support/fake-google-slides/`, a stdlib MCP server registered in each scenario's `setup.sh` on both arms. It replays decks recorded from the live connectors: the onboarding deck (2026-10-21), the brand template, Drive `copy_file` and `create_file` (2026-10-24), and the poster deck `acme-poster-fixture` for `new-slides-illustrated-deck` (2026-10-26; graded in the 2026-10-26 section above). It applies text edits, creates (images included since 2026-10-26), duplicates, deletes, transforms, shape properties and slide moves, so re-reads and the Drive text view reflect them. Before `iteration_03`, transforms and slide moves were logged but not applied, and one trial sample spent 290 s fighting shapes that never moved. Every scenario except `missing-workspace-asks-first` installs a short stand-in `google-workspace` skill on both arms; the bundled one isn't licensed for copying.
