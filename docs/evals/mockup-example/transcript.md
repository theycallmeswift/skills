# mockup — example run

One real run of the `mockup` skill, recorded 2026-10-11 with Claude Code 2.1.296 headless (`claude -p … --plugin-dir <this repo> --output-format stream-json --verbose --permission-mode acceptEdits --add-dir skills/mockup`, hosted-page tools disallowed so nothing was published) in a copy of the `leave-confirmation` eval workspace: a README for an 80×24 terminal booth app and a stub `src/screens/challenge.ts`. The agent's messages are verbatim; tool calls are one-line summaries. Headless `acceptEdits` denies writes outside the workspace and unlisted shell commands, which explains the four denials below. 12 turns, 162 s.

Output: [`v1-leave-confirm.html`](v1-leave-confirm.html), shown at phone width in [light](v1-phone-light.png) and [dark](v1-phone-dark.png).

## User

> mock up the leave-confirmation dialog for the challenge screen

## Agent

- **Skill** `core:mockup` (args: "leave-confirmation dialog for the challenge screen") — loads `SKILL.md`.

> Let me look at the project first.

- **Bash** list the workspace files and the skill's `assets/` — `README.md`, `src/screens/challenge.ts`; `NOTICE`, `page-template.html`.
- **Read** `README.md`.
- **Read** `src/screens/challenge.ts`.
- **Read** `assets/page-template.html`.
- **Bash** write a Python generator for the 80×24 grids to a scratch folder outside the workspace — denied.

> The heredoc didn't go through, so I'll write the script as a file.

- **Write** the generator script outside the workspace — denied.
- **Write** a column-width checker outside the workspace — denied.

> I can't write the generator script outside the project, so I'll hand-write the HTML and check the column widths afterwards.

- **Write** `docs/mockups/challenge-leave-confirm/mockups/v1/leave-confirm.html` — created.
- **Bash** a Python one-liner to check every grid row is 80 columns — denied (needs approval).

> Round 1 is ready, with three ways to confirm leaving a challenge. Each is drawn on the station's real 80×24 screen over a sample challenge.
>
> **Open:** `docs/mockups/challenge-leave-confirm/mockups/v1/leave-confirm.html`
>
> I couldn't publish it as a page you can open on a phone, because there's no hosting tool here and the folder isn't a git repo, so you'll need to open the file directly. My check that every row lines up at exactly 80 columns didn't run because the command needed approval, so the box edges may be a column off in places.
>
> - **A. Centered modal, "Keep playing" is the default (recommended).** The challenge dims behind a small box and the timer pauses. Enter keeps playing; only `L` leaves. The box says "Your progress and score (140) will be lost, and the station resets." It needs one new overlay component.
> - **B. Status bar asks "press Esc again".** There's no overlay: the bottom bar turns amber until the next key. It's the cheapest to build, but it's easy to miss in a noisy booth, and pressing Esc twice by accident still wipes the run.
> - **C. Full-screen choice that adds "see my results".** The options are Keep playing, Leave and see my results, or Leave and reset the station. It goes back to the challenge after 20 seconds if nobody answers. This adds scope, because the Results screen would have to handle a run that ended early.
>
> I recommend **A**. People at a booth mash Enter, so Enter should be the safe choice and leaving should take a deliberate key. Pausing the timer also means the confirmation doesn't eat into the attendee's 5:00.
>
> The challenge text and the agent output behind the dialog are made up for illustration, since the repo doesn't include real challenge content.
>
> Which option do you want: A, B or C? Or tell me what's wrong or missing.
