# mockup — example run

One real run of the `mockup` skill, recorded 2026-10-11 with Claude Code 2.1.296 headless (`claude -p … --plugin-dir <this repo> --output-format stream-json --verbose --permission-mode acceptEdits --add-dir skills/mockup`, hosted-page tools disallowed so nothing was published) in a copy of the `leave-confirmation` eval workspace: a README for an 80×24 terminal booth app and a stub `src/screens/challenge.ts`. The agent's messages are verbatim; tool calls are one-line summaries. Headless `acceptEdits` denies writes outside the workspace and unlisted shell commands, which explains the 5 denials below. 14 turns, 208 s.

Output: [`v1-leave-dialog.html`](v1-leave-dialog.html), shown at phone width in [light](v1-phone-light.png) and [dark](v1-phone-dark.png). At 390px the grids render at the template's 11px floor and pan sideways; the screenshots show their left half.

## User

> mock up the leave-confirmation dialog for the challenge screen

## Agent

- **Skill** `core:mockup` (args: "leave-confirmation dialog for the challenge screen") — loads `SKILL.md`.
- **Bash** list the workspace files and the skill's `assets/` — `README.md`, `src/screens/challenge.ts`; `NOTICE`, `page-template.html`.
- **Read** `README.md`.
- **Read** `src/screens/challenge.ts`.
- **Read** `assets/page-template.html`.
- **Read** `assets/NOTICE`.
- **Bash** write a Python generator for the 80-column grids to a scratch folder outside the workspace — denied.
- **Write** the generator script outside the workspace — denied.

> I'm drawing three versions of the leave dialog at the station's real 80×24 size. My helper script didn't save to a temporary folder, so I'm generating the mockups in a different way.

- **Bash** create `docs/mockups/challenge-leave-dialog/mockups/v1/` and run the generator inline — denied (flagged by the shell parser).
- **Bash** run the generator inline again — denied (needs approval).

> Running scripts needs your approval, so I'm writing the mockup page directly instead and will check the column widths afterwards.

- **Write** `docs/mockups/challenge-leave-dialog/mockups/v1/leave-dialog.html` — created.
- **Bash** count each grid row's width — denied (needs approval).

> I've saved the first round of mockups to `docs/mockups/challenge-leave-dialog/mockups/v1/leave-dialog.html`. Open it in a browser to see the three options at the station's real 80-column size. I couldn't check that every row is exactly 80 characters: the check needs a shell command you haven't approved. I counted the columns by hand, so one row could be off by a character.
>
> When an attendee presses **Esc** during a challenge:
>
> - **A: pop-up, timer paused** (recommended). A dialog saying "Leave the challenge?" appears over the dimmed screen. It says their score (140) won't be saved, and the timer pauses at 3:12. Enter or Esc keeps playing; only **L** leaves. At a booth, people mash keys, so leaving should take a key you only press on purpose. The cost: if someone walks away with the dialog open, the station stays on it until the idle reset.
> - **B: status bar only, press Esc twice.** There's no pop-up. The status bar turns orange for 3 seconds and says "Esc again to leave — score 140 will be lost", and the timer keeps running. It's the easiest to build, but a double-tap on Esc still throws the run away.
> - **C: like A, but the timer keeps running and the station resets itself.** The dialog says "Resetting in 0:15 unless you press Enter", so the station goes back to Attract if nobody answers. This handles walk-aways, but an attendee who only stepped back for a moment loses their run.
>
> The challenge text in the mockups is a stand-in (an `is_palindrome` task); the dialog and status-bar wording is what I'm proposing.
>
> Which one, A, B or C? Or tell me what's wrong or missing.
