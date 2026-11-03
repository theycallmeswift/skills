# MLH sources: a starting map

The main places MLH data lives and the traps each one sets. It isn't complete: when the goal needs data from somewhere else (finance, CRM, ads, analytics, a partner's own research), find it and use it, recording the source the same way. Quirks are as of Nov 2026; if one stops matching what you see, trust the data and tell the user.

## MLH Core warehouse

The system of record for the census, hackathons, events, applications and programs. Preflight with the server list plus a test query.

- **Season Census:** count only respondents who passed the attention check. Season waves aren't calendar quarters (2026 Q1 = Jul, Q2 = Oct); label waves by month. The two 2025 waves have no stored field month. Confirm how next-gen vs professional is derived (employment status or self-ID) before you label a segment, and state it once in Methodology. Find the exact question wording; if no item asks it, say "no item" rather than use a proxy.
- **Hackathons:** count hackathon-format League events only, excluding non-hackathon programs. Match a technology on built-with tags or prize-challenge names, and also report tag-only. A 2026 "AI tools used" re-import inflated Q3 2026; confirm its date and exclude it. Label partly loaded quarters as provisional. Confirm in the warehouse before saying a partner sponsored nothing.
- **Programs and fellowships:** applications carry type, stage and track in JSON fields; read those rather than stale status columns. Join people on email; program IDs don't match user IDs. Admissions can route applicants across tracks, so "admitted to X" isn't "applied for X".

## DEV warehouse (dev.to)

The 2026 account surge (from about February, spiking in April) breaks raw counts. Use distinct authors and posts with at least one reaction, each as a share of the platform total. Tags and title themes (including complaints) show what developers say about a tool.

## Forms (Typeform)

Program and event surveys, mentor surveys, hiring and alumni forms, registrations. Read-only. Compute n for each item. Paraphrase free text; don't name respondents.

## Drive: decks, sheets, docs

Decks (check speaker notes and figures that only appear in chart images), raw survey exports, tracking sheets, SOWs and proposals. Prefer the sheet behind a deck. Record the file, tab and range for every number.

## Slack, email, meetings

- **Slack:** relationship health, internal metrics, decisions, sensitivities, timelines. Read whole threads and keep permalinks. Treat bot-posted figures as unverified.
- **Email:** contacts and roles, asks, MLH commitments, signed dates, figures sent externally. Read-only.
- **Meeting notes and transcripts:** skim notes, then search transcripts for specifics. Paraphrase; name spellings are unverified.

## AI search visibility (Gauge)

How AI answers mention and cite brands, top-cited pages, keyword volumes. Confirm the org first. Use read tools only; some tools spend credits.

## Web benchmarks

Latest edition of each: Stack Overflow Developer Survey, JetBrains State of Developer Ecosystem, CNCF, DORA, Menlo/a16z, and the subject's own research. Open every page you cite. Record the exact question and sample; wording decides whether two figures compare.
