# MLH sources: a starting map

The main places MLH data lives and the traps each one sets. It isn't complete: when the goal needs data from somewhere else (finance, CRM, ads, analytics, a partner's own research), find it and use it, recording the source the same way. Quirks are as of Nov 2026; if one stops matching what you see, trust the data and tell the user.

## MLH Core warehouse

The system of record for the census, hackathons, events, applications and programs. Preflight with the server list plus a test query. Its tools point to `core-data-model` (and, for DEV, `dev-queries` and `dev-limitations`) resources; read them if you can. The traps below are the ones that cost past runs.

- **Season Census:** seasons run July to June: Season 2025 Q3 = Jan 2026, Q4 = Apr 2026; Season 2026 Q1 = Jul 2026, Q2 = Oct 2026. Label waves by month. Season 2025 Q1 and Q2 aren't in the warehouse, so there is no calendar-2025 baseline.
  - Attention check: "Just checking in! … Please click 'Strongly disagree'" (QID1219624549; QID1219198910 in Jan 2026), pass = code 8. Count passers only. About half the rows drop out before the check; exclude them too.
  - Decode per question and per wave. Single-choice answers store Qualtrics RecodeValues, but `survey_value_mappings` is keyed on choice IDs, so decoding through it mislabels with no error. Read labels from `surveys.description->'result'->'Questions'->QID->'RecodeValues'`. Codes are reused across questions and waves (37 = Claude Desktop in Jan 2026, Claude Code after). Check that every stored code has a label, and trend only options offered under the same label in both waves.
  - One question can span several QIDs in a wave (display-logic branches): combine them. Join on `answers->>'question_id'`, not `provider_field_id`. Some fields have no stored answers (dead duplicates, or not asked that wave), so count answers per QID per wave before planning a trend. `DisplayLogic` says who was asked; that is the base.
  - Multi-select "None of the above" is never stored; those respondents have an empty array. Denominator: everyone shown the item. Say so in the caption.
  - Segments: next-gen = Student (full- or part-time) on the employment-status item; professional = employed (full-time, part-time or self-employed) and not a student; everyone else counts only in "all". Professionals are about 500–600 per wave vs about 2,800 next-gen.
  - Find the exact question wording; if no item asks it, say "no item" rather than use a proxy.
  - Unnesting all responses with `jsonb_array_elements` times out; filter per `survey_id` with `@>` or `@?`.
- **Hackathons:** League hackathons = `programs.name = 'League'` and `events.event_format = 'hackathon'` (not `series`); drop test events. Hack Days, GHW and Hacktoberfest are separate programs. Count distinct projects on `EventSubmission` rows; `project_submissions` also holds `ChallengeSubmission` rows, which double the count. Reach prize challenges through `project_submissions.challenge_id` (`event_challenges` is incomplete). `built_with` is sometimes one comma-joined string: split and trim. Match a technology on built-with tags, and show it with and without events where that vendor had a prize; for a tool devs build with, the prize is the confound. `projects.ai_tools` exists only on projects loaded from Oct 2026 (mostly Hack Days): don't trend it. Label partly loaded quarters as provisional. Confirm in the warehouse before saying a partner sponsored nothing. `companies.name` carries contract periods ("Snowflake Q3 2025 - Q1 2026"): never copy it into reader-facing text.
- **Participation:** many 2025 externally hosted League events have no `participations` rows (165 of 223 do; in 2026, 212 of 220), so participations overstate YoY growth. Compare only events with rows in both years, or use `events.check_ins_count` for both years, and say which. Hacktoberfest (from Oct 2026; match `events.name ILIKE '%hacktoberfest%'`) auto-checks-in digital attendees: about 470 events and 100k people. That is about half of 2026 participants, and it drove the Oct 2026 spike in Core sign-ups (274k vs about 60k a month). Report digital and in-person separately, and show any 2026 headline with and without Hacktoberfest.
- **People:** `user_profiles.gender` and `race_or_ethnicity` are free text in many languages, and `country_of_residence` is missing for most 2026 participants. Use the census's structured items and physical event addresses instead.
- **Programs and fellowships:** applications carry type and track in JSON fields. Join people on email; program IDs don't match user IDs. Admissions can route applicants across tracks, so "admitted to X" isn't "applied for X". For Fellowship, `applications.metadata->>'stage'` is null and `crm_stage_name` is the only live stage. `fellowship_enrollments` was backfilled in Mar 2026, has no 2026 cohorts, leaves post-2023 cohorts at "Enrolled", and disagrees with CRM (57 vs 130 for 2025). Confirm counts with the program team.

## DEV warehouse (dev.to)

Post volume runs 2–4x normal from about April 2026, mostly posts with no reactions; account sign-ups show no 2026 surge. Use posts with at least one reaction. From mid-2026 even those roughly doubled, so prefer within-topic shares (a tool's share of posts on the topic) over share of the platform. Platform-wide aggregates on `articles` and `users` time out even for one month: chunk by week or ID range, or report within-set ratios and say so. DEV challenges (`devchallenge` tag) spike a sponsor's tag, so show tag shares with and without them. Tags and title themes (including complaints) show what developers say about a tool.

## Forms (Typeform)

Program and event surveys, mentor surveys, hiring and alumni forms, registrations. Read-only. Compute n for each item. Paraphrase free text; don't name respondents.

## Drive: decks, sheets, docs

Decks (check speaker notes and figures that only appear in chart images), raw survey exports, tracking sheets, SOWs and proposals. Prefer the sheet behind a deck. Record the file, tab and range for every number.

## Finance

Revenue truth, best first: closed books (QuickBooks; no connector, so ask, or use a management P&L the user supplies, labeled pro forma) > the Deferred Revenue Schedule sheet (`1ZO8WF7gP0Pc7UP7mmcEJhdf9L5r06akbM2uUgElG3qc`, the official schedule the books follow) > ad-hoc exports > Slack. In the schedule, months after the current one are scheduled, not recognized. Total is net of Discounts, and product rows don't sum to Events. The Bookings and Upcoming Renewals tabs are stale. Recognized revenue, bookings and CARR are different numbers: pick one per claim. Cash, burn and runway come from the books' balance sheet: ask for them.

## Slack, email, meetings

- **Slack:** relationship health, internal metrics, decisions, sensitivities, timelines. Read whole threads and keep permalinks. Treat bot-posted figures as unverified.
- **Email:** contacts and roles, asks, MLH commitments, signed dates, figures sent externally. Read-only. Read whole threads; search results preview only the oldest messages.
- **Meeting notes and transcripts:** skim notes, then search transcripts for specifics. Paraphrase; name spellings are unverified.

## AI search visibility (Gauge)

How AI answers mention and cite brands, top-cited pages, keyword volumes. Confirm the org first. Use read tools only; some tools spend credits.

## Web benchmarks

Latest edition of each: Stack Overflow Developer Survey, JetBrains State of Developer Ecosystem, CNCF, DORA, Menlo/a16z, and the subject's own research. Open every page you cite. Record the exact question and sample; wording decides whether two figures compare.
