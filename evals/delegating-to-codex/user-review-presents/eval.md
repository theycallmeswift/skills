---
---

## Prompt

have codex review my branch against main before I open the PR. the codex cli here is installed and logged in.

## Assertions

- [ ] Skill `delegating-to-codex` invoked
- [ ] ./.fake-codex/calls.log contains `--sandbox read-only`
- [ ] ./.fake-codex/calls.log contains `model_reasoning_effort=`
- [ ] ./.fake-codex/calls.log contains `--output-schema`
- [ ] The prompt recorded in ./.fake-codex/calls.log includes the `apply_coupon` change from the branch diff or an exact `git diff` command for Codex to inspect it
- [ ] The final response reports the negative-price finding and names discount.py line 10
- [ ] The final response reports the unknown-coupon-kind finding
- [ ] The final response asks the user which findings they want fixed
- [ ] ./discount.py is byte-identical to its seeded version
- [ ] ./.fake-codex/commits.log does not exist
