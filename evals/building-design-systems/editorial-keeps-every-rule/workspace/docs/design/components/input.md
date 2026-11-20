# Input

Text inputs collect things like service names, branch names and rollback reasons.

## Size and shape

Inputs are 40px tall, a little taller than buttons, because typing targets should be generous. They have a 1px border and the standard 6px radius, matching buttons so forms look consistent.

## States

Inputs support default, focus-visible, disabled and invalid.

- **Focus-visible:** the same 2px ring in the accent blue `#2563EB` with a 3px offset that buttons use. Consistency matters here: users learn one focus style.
- **Disabled:** 0.45 opacity, the same as buttons.
- **Invalid:** the border turns `#DC2626` and the input sets `aria-invalid="true"`. An error message in `#DC2626` appears below the field. Remember that the error text is text, so it must reach 4.6:1 against the background.

## Spacing

Labels sit 8px above the input, and helper or error text sits 4px below it.
