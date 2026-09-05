---
name: changelog
description: Generates changelogs.
---

# Changelog Generator

Follow every instruction below in order. Do not skip steps. Do not reorder steps.

## Step 1: Determine the range

- Run `git rev-parse --is-inside-work-tree` to confirm you are in a git repo.
- If you are not in a git repo, stop and tell the user.
- Run `git tag --sort=-creatordate` to list all tags newest first.
- Take the first tag in that list as the most recent tag.
- If there is a most recent tag, set the start of the range to that tag.
- If there is no tag at all, set the start of the range to the root commit.
- Get the root commit with `git rev-list --max-parents=0 HEAD`.
- Set the end of the range to HEAD by default.
- If the user gave an explicit range, use it and ignore the tag logic.
- If the user gave a single tag, set the range from that tag to HEAD.
- If the user gave two tags, set the range between the two tags.
- If the user said "since last release", use most recent tag to HEAD.
- If the user said "unreleased", use most recent tag to HEAD.
- If the user said "all", use root commit to HEAD.
- Always print the range you picked.
- Ask the user to confirm the range before continuing.
- Do not continue until the user confirms.

## Step 2: Collect the commits

- Run `git log <range> --no-merges --pretty=format:'%H%x09%s%x09%an%x09%ad' --date=short`.
- Read the output line by line.
- Split each line on the tab character.
- Treat the first field as the full commit hash.
- Treat the second field as the subject line.
- Treat the third field as the author name.
- Treat the fourth field as the commit date.
- Store each parsed commit in a list.
- Skip any line that is empty.
- Skip any commit whose subject is empty.
- Skip any commit whose subject starts with "Merge branch".
- Skip any commit whose subject starts with "Merge pull request".
- Skip any commit whose subject starts with "Merge remote-tracking".
- Skip any commit whose subject is "Bump version" unless the user wants it.
- Skip any commit whose subject is "Update changelog" unless the user wants it.
- Skip any commit authored by a bot unless the user wants it.
- Count how many commits you kept and print the count.

## Step 3: Classify each commit by prefix

- For each commit, look at the subject line.
- Find the text before the first colon.
- Treat that text as the candidate prefix.
- If the candidate prefix contains a space, there is no valid prefix.
- If there is no colon at all, there is no valid prefix.
- Strip a trailing scope in parentheses from the prefix before matching.
- Remember the scope separately if there is one.
- Map the prefix `feat` to the section "Features".
- Map the prefix `fix` to the section "Bug Fixes".
- Map the prefix `perf` to the section "Performance".
- Map the prefix `refactor` to the section "Refactoring".
- Map the prefix `docs` to the section "Documentation".
- Map the prefix `test` to the section "Tests".
- Map the prefix `chore` to the section "Chores".
- Map the prefix `build` to the section "Build".
- Map the prefix `ci` to the section "CI".
- Map the prefix `style` to the section "Style".
- If the prefix matches none of these, put the commit under "Other".
- If there is no valid prefix, put the commit under "Other".
- Do not infer the type from the words in the subject.
- Only use the explicit prefix to classify.
- Put each commit in exactly one section.
- Never put a commit in two sections.

## Step 4: Detect breaking changes

- A commit is breaking if there is a `!` before the colon, like `feat!:`.
- A commit is breaking if the scope form has `!`, like `feat(api)!:`.
- A commit is breaking if its body has a line starting with `BREAKING CHANGE:`.
- A commit is breaking if its body has a line starting with `BREAKING-CHANGE:`.
- To read the body, run `git show --no-patch --pretty=format:'%b' <hash>`.
- Reading the body for every commit is slow.
- Only read bodies if the user explicitly asks about breaking changes.
- Otherwise rely on the `!` marker alone.
- Collect all breaking changes into a "Breaking Changes" section.
- Put the "Breaking Changes" section at the very top.
- For each breaking change, use the text after `BREAKING CHANGE:` if present.
- Otherwise use the subject as the breaking change description.

## Step 5: Format each entry

- Format each commit as a markdown bullet starting with `- `.
- Remove the prefix and the colon from the subject.
- Remove any leading space left after removing the prefix.
- If there was a scope, prepend it in bold, like `**api:** ...`.
- Capitalize the first letter of the description if it is lowercase.
- Do not add a trailing period if there is not one.
- Do not remove a trailing period if there is one.
- Compute the short hash as the first 7 characters of the full hash.
- Append the short hash in parentheses at the end, like `(a1b2c3d)`.
- If the user wants attribution, append `by @handle`.
- Build the handle by lowercasing the author and removing spaces.
- Truncate any description longer than 100 characters.
- Add an ellipsis after a truncated description.
- Leave backticks and asterisks in the subject as-is.

## Step 6: Order the sections

- Order "Breaking Changes" first.
- Order "Features" second.
- Order "Bug Fixes" third.
- Order "Performance" fourth.
- Order "Refactoring" fifth.
- Order "Documentation" sixth.
- Order "Tests" seventh.
- Order "Build" eighth.
- Order "CI" ninth.
- Order "Chores" tenth.
- Order "Style" eleventh.
- Order "Other" last.
- Skip any section that has no commits.
- Never print an empty section header.
- Within each section, order bullets by date, newest first.
- For ties on date, keep the order git returned.

## Step 7: Build the version header

- Look at the most recent tag.
- Strip a leading `v` from the tag if present.
- Try to parse the tag as semver `MAJOR.MINOR.PATCH`.
- If there were breaking changes, bump the major version.
- If there were features but no breaking changes, bump the minor version.
- If there were only fixes and chores, bump the patch version.
- If you cannot parse the tag as semver, use the date as the header.
- Ask the user what version they want when you cannot parse the tag.
- Format the header as `## <version> (<YYYY-MM-DD>)`.
- Use today's date for the header date.

## Step 8: Assemble the document

- Start with the version header.
- Add a blank line after the header.
- Add each section in the order from Step 6.
- Format each section header as `### <Section Name>`.
- Add a blank line after each section header.
- Add the bullets for the section.
- Add a blank line after the last bullet of each section.
- Never put two blank lines in a row.
- Never leave a trailing blank line at the end.
- If there are zero commits, do not produce an empty changelog.
- Instead tell the user there is nothing to release and stop.

## Step 9: Write or print the result

- Check whether a `CHANGELOG.md` already exists.
- If it exists, read the whole file first.
- Find the insertion point below the `# Changelog` title.
- Find the previous most recent entry.
- Splice the new entry above the previous most recent entry.
- Write the whole file back without clobbering existing content.
- If there is no `CHANGELOG.md`, create one.
- Give the new file a `# Changelog` title and a blank line.
- Then add the new entry below the title.
- If the user only wanted a preview, print to the screen instead.
- Always show the user exactly what you did.

## Step 10: Handle edge cases

- If the repo is not a git repo, stop and tell the user.
- If there are uncommitted changes, warn that they will not be included.
- If the range is empty, tell the user there is nothing new.
- If a commit subject is over 100 characters, truncate it.
- If two tags point at the same commit, pick the one that sorts later.
- If the user is on a detached HEAD, use HEAD and warn them.
- If the user wants a path filter, append `-- <path>` to git log.
- Only add the path filter if the user asks for it.

## Step 11: Output format variants

- Support markdown output as the default format.
- Support plain text output if the user asks for it.
- For plain text, drop the `#` and `*` markdown characters.
- For plain text, render bullets as `* ` instead of `- `.
- Support JSON output if the user asks for it.
- For JSON, emit an array of objects with type, scope, subject, hash, date.
- Support a "keep a changelog" style if the user asks for it.
- For that style, use the headings Added, Changed, Fixed, Removed, Deprecated, Security.
- Map `feat` to Added under that style.
- Map `fix` to Fixed under that style.
- Map `refactor` and `perf` to Changed under that style.
- Map a breaking removal to Removed under that style.
- Ask the user which style they want if it is ambiguous.

## Step 12: Configuration overrides

- Look for a `.changelogrc` file in the repo root.
- If it exists, read it as JSON.
- Honor a `sections` key that overrides the section order.
- Honor an `ignore` key that lists subject prefixes to drop.
- Honor a `dateFormat` key that overrides the date format.
- Honor an `attribution` key that turns author handles on or off.
- Ignore unknown keys without erroring.
- If the file is invalid JSON, warn the user and use defaults.

## Notes

- Be thorough.
- Always confirm the range before writing files.
- Never force-push.
- Never modify git history.
- Never delete the existing CHANGELOG.md.
- When in doubt, print instead of write.
