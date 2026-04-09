# Prompt Engineer Rubric

Evaluated by `make eval`.

## Critical

- The produced prompt explicitly instructs the LLM to return only JSON with no prose wrapper, markdown fences, or commentary (for `contract-extraction-json`)
- The produced prompt specifies behavior when a required field is missing (null vs omit vs error) (for `contract-extraction-json`)
- The produced prompt addresses long or multi-page inputs (chunking, truncation, or explicit full-document processing) (for `contract-extraction-json`)
- Output contains a Changes section (or equivalent) explaining what was fixed and why (for `fix-bad-prompt`)
- The diagnosis identifies at least two of: vague role, contradictory instructions, politeness padding, missing output format (for `fix-bad-prompt`)
- The rewritten prompt removes "helpful AI assistant", "please", and "thank you" padding (for `fix-bad-prompt`)
- The rewritten prompt specifies a concrete output format (for `fix-bad-prompt`)
- The rewritten prompt resolves the "thorough but concise" contradiction (for `fix-bad-prompt`)
- For `vague-summarization-request`: output does not fabricate specifics the user did not provide

## Optional

- The rewritten prompt is shorter than the original (for `fix-bad-prompt`)
