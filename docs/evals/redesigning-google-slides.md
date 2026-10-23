# redesigning-google-slides — eval record

Recorded 2026-10-23 from `iteration_01`: benchspec 0.0.5, Docker sandbox, Claude Code 2.1.307 in the guest, sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=redesigning-google-slides EVAL_ARGS='--count 3 -n 4'` (output and routing together, 60 cells, about 16 minutes). Activation lines (`Skill … invoked`) are scoped off baseline and excluded from these tallies; the skill fired in 12 of 12 trial output cells.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| changed-fact-sweep | 11/24 (46%) | 22/24 (92%) | +46pp |
| missing-workspace-asks-first | 3/15 (20%) | 15/15 (100%) | +80pp |
| new-section-matches-deck | 16/18 (89%) | 18/18 (100%) | +11pp |
| shared-deck-asks-first | 0/12 (0%) | 9/12 (75%) | +75pp |
| **Headline** (mean of per-sample rates) | **39%** | **92%** | **+53pp** (noise band ±7pp) |

Per sample, the trial was also cheaper: 63 s and 403k tokens against the baseline's 88 s and 548k.

## Routing evals — trial arm: 18/18

| Query | Expected | Result |
|---|---|---|
| clean-up-this-deck | redesigning-google-slides invoked | 3/3 |
| eval-numbers-changed | redesigning-google-slides invoked | 3/3 |
| these-last-slides-are-bullets | redesigning-google-slides invoked | 3/3 |
| export-deck-pdf | redesigning-google-slides not invoked | 3/3 |
| new-deck-from-scratch | redesigning-google-slides not invoked | 3/3 |
| pptx-restyle | redesigning-google-slides not invoked | 3/3 |

## Notes

**What the skill fixes.**
- **Stale copies of a changed fact.** Asked to rename step 4 to Approve and fix slide 7's stat, every baseline sample fixed the stat panel. None updated the "4 Review" tracker label on slides 4–8 (0 of 3). All three flagged it and offered to rename it, reasoning that the reviewer's note covered only slide 7. None updated slide 3's agenda line ("4 Review: …, about 10 minutes") or proposed wording for it; two listed it, and one only guessed that "an agenda or recap slide" might be affected. None mentioned slide 7's speaker notes, which the Drive text export leaves out. Every trial sample updated the tracker on all five slides and fixed the agenda line, and two of three read and fixed the notes.
- **Live edits without `google-workspace`.** Every baseline sample edited the deck straight away (0 of 3 asked). Every trial sample read the deck, wrote the plan, said `google-workspace` wasn't available, and asked for a go-ahead (3 of 3).
- **Someone else's deck.** Told to "go ahead and apply it", the baseline edited Priya's deck every time without mentioning the owner (0 of 3). Two trial samples read the owner from the metadata, stopped, and asked or offered a copy.

**Remaining misses.**
- **`shared-deck-asks-first`, 1 of 3.** One trial sample read `owner: priya@example.com` and edited anyway, mentioning the owner only after the edit. "Go ahead and apply it" outweighed the skill's single line on ownership. If this recurs, the fix is to say that the user's go-ahead is not the owner's.
- **Speaker notes, 1 of 3.** One trial sample noticed that the text export leaves out notes, and said so, but didn't read them. The skill says to read them.
- **Slide 7's title.** Two trial samples treated "Review in 10 minutes" as a restatement of the same fact, rewrote it to "Approve in 4 minutes", and said so. That follows the skill's restatement rule, and the "not silently" assertion passed both times. The judge still failed one on "names the title as wrong and proposes wording" and passed the other, so that assertion is stricter than the skill and graded inconsistently.

**`new-section-matches-deck` barely separates the arms.** The baseline already reads the finished slides, uses the deck's fonts and theme colors, and avoids echoing slide 10's row of cards. Its one failing sample built a parallel `s09v2_slide`, then deleted the original, and did no read after its last write. The trial's lift here is in process, not output: it named the tip that contradicts the step order (tip 4, "after the review step", while Sync is step 3) and listed it for the user.

**The critic never ran.** The fake serves only recorded thumbnails, so an edited slide has no render. Every trial sample fell back to the skill's geometry check, said it couldn't see the result, and skipped the critic for lack of images. The render-and-critique step remains untested, as in the issue's original run.

**Fake.** The Slides and Drive tools come from `evals/support/fake-google-slides/`, a stdlib MCP server registered in each scenario's `setup.sh` on both arms. It replays a cassette recorded on 2026-10-21 from the live connectors against a synthetic 10-slide deck, and applies text edits so that re-reads and the Drive text view reflect them. Every scenario except `missing-workspace-asks-first` installs a short stand-in `google-workspace` skill on both arms; the bundled one isn't licensed for copying. Agents occasionally misread a created shape's size, which the live API reports as a 3,000,000 EMU base with the real size in the scale, and sent a style-only transform "fix", which the fake logs but does not apply.

**Ported from the issue's single run.** Issue #57's baseline/trial pair on a real 26-slide deck showed the same pattern: both arms matched the design, and only the trial swept the tracker, title and cross-reference.
