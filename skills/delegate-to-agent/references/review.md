# Reviewing with a delegate

Read before dispatching a review job or acting on the findings one returns.

## Order by model family

The family that wrote the code never reviews first. The delegate implemented it: review it yourself first, then send it out. You or another agent of your own family wrote it: the delegate goes first.

## Judge every finding against the code

Some findings don't hold up. Open the cited lines and decide whether each is real before acting on it. Always ask of a test: would it fail against the implementation it is meant to rule out? A test that could never fail is the most common real finding.

## Present or fix, by who asked

- **The user asked for the review.** Present each finding with its file:line and your verdict, then stop and ask which to fix — some, all, or none. Change nothing yet.
- **A plan step triggered it.** Fix the real findings yourself, or by resuming the implement job with a brief naming them; re-run the gate and commit. Don't block waiting for the user. Your final report names every finding, fixed or dismissed with the reason — a dismissed finding left out of the report looks like one you never checked.

Adjudicated findings can go back to the same thread for a re-review: `--resume <job-id>` with a brief holding only what changed. A resumed job inherits the sandbox and output schema of the job it resumes, so the re-review stays read-only and still returns JSON on its own. Don't re-pass the review flags.

## Mutation checks, where the blast radius is real

A mutation check proves a test actually guards a risk. The delegate's review sandbox is read-only, so running one is your job, and it costs a full edit-test-undo cycle. Spend it on risks that are expensive to get wrong — data loss, auth, money, corruption, a silently wrong answer — not on every risk the brief happened to name.

1. Change one thing.
2. Run one test; confirm it fails.
3. Undo with an inverse edit. Never `git checkout`, `restore`, or `stash`: they can discard other work.

End with `git status` and confirm the tree matches its prior state. An implementer's failing run can be real and still prove the wrong claim.
