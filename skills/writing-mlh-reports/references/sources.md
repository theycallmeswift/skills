# MLH sources: data traps

Traps that silently produce wrong numbers, as of Nov 2026. If one stops matching the data, trust the data and tell the user.

## MLH Core warehouse

Read its `core-data-model` resource (for DEV, `dev-queries` and `dev-limitations`) when available.

**Season Census**
- Waves: seasons run July–June (S2025 Q3 = Jan 2026, Q4 = Apr 2026; S2026 Q1 = Jul 2026, Q2 = Oct 2026). Label waves by month. S2025 Q1–Q2 aren't loaded, so there's no calendar-2025 baseline.
- Attention check: "Just checking in! … Please click 'Strongly disagree'" (QID1219624549; QID1219198910 in Jan 2026), pass = code 8. Count passers only; the ~half who drop out before it are excluded too.
- Decoding: answers store Qualtrics RecodeValues, but `survey_value_mappings` is keyed on choice IDs and mislabels without error. Read labels from `surveys.description->'result'->'Questions'->QID->'RecodeValues'` per question and wave: codes are reused (37 = Claude Desktop in Jan 2026, Claude Code after). Every stored code needs a label; trend only options offered under the same label in both waves.
- Multi-QID items: display-logic branches split one question across QIDs; combine them, join on `answers->>'question_id'` (not `provider_field_id`), and count answers per QID per wave before planning a trend (some fields are empty). `DisplayLogic` defines the base.
- Multi-select "None of the above" is never stored (empty array): the denominator is everyone shown the item; say so in its footnote.
- Segments: next-gen = Student (full- or part-time) on employment status; professional = employed (incl. self-employed) and not a student; others count only in "all". ~500–600 professionals per wave vs ~2,800 next-gen.
- Examples in an item's wording prime its answers: if the top answers are the listed examples, or the examples changed between waves, don't rank or trend it.
- No item asks it? Say "no item", not a proxy. Unnesting all responses with `jsonb_array_elements` times out: filter per `survey_id` with `@>` or `@?`.

**Hackathons**
- League hackathons = `programs.name = 'League'` and `events.event_format = 'hackathon'` (not `series`), test events dropped. Hack Days, GHW and Hacktoberfest are separate programs.
- Count distinct projects on `EventSubmission` rows (`ChallengeSubmission` rows in `project_submissions` double it). Reach prize challenges via `project_submissions.challenge_id` (`event_challenges` is incomplete).
- `built_with` is sometimes one comma-joined string: split and trim. Match brands on word boundaries (`anthropic` hits "Philanthropic" prize tracks). A 2026-09-21 re-import appended "AI tools used" answers to `built_with`, inflating Q3 2026 vendor shares (Claude 68% raw vs ~25% cleaned): exclude them. Show a technology with and without events where its vendor had a prize.
- From 2026 projects cap at two members: don't trend team size across it.
- `projects.ai_tools` exists only from Oct 2026 loads: don't trend it. Label partly loaded quarters provisional. Confirm in the warehouse before saying a partner sponsored nothing. `companies.name` embeds contract periods: never copy it into reader text.

**Participation**
- Many 2025 externally hosted League events lack `participations` rows (165 of 223 have them; 2026: 212 of 220), inflating YoY growth. Compare only events with rows in both years, or use `events.check_ins_count` for both, and say which.
- Hacktoberfest (from Oct 2026; `events.name ILIKE '%hacktoberfest%'`) auto-checks-in digital attendees: ~470 events, ~100k people, half of 2026 participants, and the Oct 2026 Core sign-up spike (274k vs ~60k/month). Report digital and in-person separately; show 2026 headlines with and without it.

**People and programs**
- `user_profiles.gender` and `race_or_ethnicity` are multilingual free text; `country_of_residence` is missing for most 2026 participants. Use census items and event addresses.
- Join applicants on email (program IDs ≠ user IDs). Admissions route across tracks: "admitted to X" ≠ "applied for X". Fellowship's only live stage is `crm_stage_name`; `fellowship_enrollments` has no 2026 cohorts and disagrees with CRM (57 vs 130 for 2025). Confirm counts with the program team. Program outcomes mostly live outside the warehouse: Typeform (n varies per item), Drive tracking sheets and the sheet behind each deck.

## DEV warehouse (dev.to)

- Post volume runs 2–4x normal from ~April 2026, mostly zero-reaction posts (sign-ups didn't surge). Count posts with ≥1 reaction; even those ~doubled from mid-2026, so prefer within-topic shares over platform share.
- Platform-wide aggregates on `articles` and `users` time out even for a month: chunk by week or ID range, or report within-set ratios and say so.
- `devchallenge` posts spike a sponsor's tag: show tag shares with and without them.

## Finance

Revenue truth, best first: closed books (QuickBooks, no connector: ask, or label a supplied management P&L pro forma) > Deferred Revenue Schedule sheet (`1ZO8WF7gP0Pc7UP7mmcEJhdf9L5r06akbM2uUgElG3qc`) > ad-hoc exports > Slack. In the schedule, months after the current one are scheduled, not recognized; Total is net of Discounts; product rows don't sum to Events; Bookings and Upcoming Renewals tabs are stale. Recognized revenue, bookings and CARR differ: pick one per claim. Cash, burn and runway come from the balance sheet: ask.

## Elsewhere

Use the sheet behind a deck, checking speaker notes and chart images. Bot-posted Slack figures are unverified. Email search previews only a thread's oldest messages: read whole threads.
