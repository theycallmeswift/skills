# booth-portal

The terminal app on our conference booth stations. Attendees walk up, play a
short timed coding challenge against an AI agent, and the station wipes itself
for the next person. It is a full-screen terminal UI (TypeScript, OpenTUI),
driven by the keyboard only, in an 80×24 window.

## Screens

- **Attract**: idle loop with the booth logo; any key starts.
- **Challenge**: the prompt on the left, the agent's live output on the right,
  a countdown (5:00) and the score in the status bar. `Esc` leaves.
- **Results**: final score, leaderboard rank, and an email sign-up.

Leaving a challenge throws away the attendee's progress and returns the station
to Attract.
