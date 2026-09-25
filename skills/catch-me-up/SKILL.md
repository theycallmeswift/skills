---
name: catch-me-up
description: Use when the user returns to this session after a break and wants re-orienting on it — "catch me up", "where were we", "I'm back", "bring me up to speed on this one", "I lost the thread", "recap this session", "what's the state of this session", "what's left", "what's blocking and what's on me", "what needs my call". Fires in a repository or not; research and planning threads count. Do NOT use for news or articles (summarize), a survey across repos or sessions, the status of one named PR, listing PRs, recapping specific commits or a file's recent changes, summarizing what a repo does, or explaining a file, function, or tool.
---

# catch-me-up

Re-orient a reader who is coming back cold to *this* session. The narrative comes from the conversation; every hard fact is checked against the workspace before it is stated. The conversation is a record of what someone *said* happened — it goes stale, and the reader will act on whatever you tell them.

## 1. Check what the conversation is missing

Do this first, before touching the workspace. Read the first turn. If it opens mid-thought — a reply starting with "…", references to decisions you can't see, a summary standing in for earlier turns — the start of the conversation is gone. That gap is in *your context*, not in the workspace: the TL;DR says earlier context is missing, the recap covers only what survives, and you don't reconstruct the missing start or blame the gap on missing files.

## 2. Check what the conversation claims

List the conversation's concrete claims about the workspace and check each. Read-only: don't fix, commit, or push anything. This is a recap, not a review — confirm that claimed things exist and match their description; don't critique the code or hunt for bugs.

- **Files.** Every file the conversation says was written or changed: confirm it exists and matches what was described. A file promised or discussed but not there is *not done*.
- **Branch and tree.** In a git repository: `git status --short --branch` for branch, upstream, and uncommitted changes; `git log --oneline <default-branch>..HEAD` for its commits.
- **Pull request and CI.** If `gh` is available: `gh pr view --json number,state,url,statusCheckRollup` for the current branch. Git alone can't tell you whether a PR exists or what its checks say — don't infer either from commits or remotes.

Skip checks that don't apply, silently: no repository, no git statements; no `gh` or no PR, no PR statements. A claim you can't check — a test run, a manual test — goes in Cliff Notes as *unverified*, in place of the conversation's version. It is not a task for the user.

**Where the conversation and the workspace disagree, the workspace wins.** Report the observed state and name the contradiction in one line ("the session ended saying CI was green; PR #12's `lint` check is failing") so the reader knows which memory to discard.

## 3. Write the recap

The first line of the reply is `### TL;DR`. That line is what a returning reader sees first; a status line about your checks ahead of it buries the recap. Not "Both files check out.", not "Now I have what I need." — nothing before the heading. What the checks found goes in Cliff Notes. One shape, every time. The reader has no project context: name the repo or topic and what it's for before the update, gloss tool names and jargon on first use, and give the *why* before the *what*.

```
### TL;DR

<1–2 sentences of plain body text — not a heading, not bold. What this is, where it stands, and the one thing that most needs attention. If earlier context is missing, say so here.>

***

### Cliff Notes

- **<Name or critical fact>:** <1–2 sentences; *italics* for nuance.>
- … 5–8 bullets, ordered by importance, not chronology.

***

### Next Up

**You:** <decisions or actions only the user can take — or "Nothing is waiting on you." when that's true>

**Me:** <what the agent can clear without a decision — or "Nothing queued.">
```

- Separate sections with `***`, never `---`.
- **You:** only decisions the conversation left open for the user, or a contradiction that blocks progress until they act. Unverified claims, your own observations about the code, and "confirm this is intentional" questions are not items. Don't manufacture one to fill the slot; an empty slot is information.
- With no repository, still emit all three sections, and make no branch, PR, or CI statement anywhere in the reply — not in a bullet, not even that there isn't one.
