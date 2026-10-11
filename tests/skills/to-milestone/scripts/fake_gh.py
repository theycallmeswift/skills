#!/usr/bin/env python3
"""A fake `gh` that serves the slice of GitHub's REST API milestone.py calls.

State lives in the JSON file `FAKE_GH_STATE` names, and every argv is appended to
`FAKE_GH_LOG`. Like GitHub, an issue's REST id differs from its number (id = number + 1000),
and a blocked-by link names the blocker by id, so passing a number fails with Not Found.

Knobs: `FAKE_GH_OFFLINE=1` fails every call the way gh does offline; `FAKE_GH_MAX_LINKS=N`
keeps only the first N blockers per issue; `FAKE_GH_FAIL_ON=<METHOD path-substring>` fails
every matching call.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import NoReturn

ID_OFFSET = 1000


def fail(message: str) -> NoReturn:
    """Exit the way gh does when the API returns an error."""
    print(message, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """Serve one `gh api` call."""
    arguments = sys.argv[1:]
    with open(os.environ["FAKE_GH_LOG"], "a") as log:
        log.write(" ".join(["gh", *arguments]) + "\n")

    if os.environ.get("FAKE_GH_OFFLINE") == "1":
        fail("error connecting to api.github.com")
    if arguments[:1] != ["api"]:
        fail(f"fake gh: unsupported command: {arguments}")

    method = arguments[arguments.index("-X") + 1] if "-X" in arguments else "GET"
    path = next(argument for argument in arguments[1:] if "/" in argument)
    body = json.loads(sys.stdin.read()) if "--input" in arguments else None

    fail_on = os.environ.get("FAKE_GH_FAIL_ON", "")
    if fail_on:
        fail_method, _, fail_path = fail_on.partition(" ")
        if method == fail_method and fail_path in path:
            fail("HTTP 502: Server Error")

    state_path = Path(os.environ["FAKE_GH_STATE"])
    state = json.loads(state_path.read_text())
    response = route(state, method, path.split("?")[0], body)
    state_path.write_text(json.dumps(state))
    print(json.dumps(response))


def route(state: dict, method: str, path: str, body: dict | None):
    """Apply one call to the state and return GitHub's response."""
    repo = state["repo"]
    issues = state.setdefault("issues", {})

    if (method, path) == ("GET", f"repos/{repo}"):
        return {"full_name": repo}
    if path == f"repos/{repo}/milestones":
        if method == "GET":
            return state.setdefault("milestones", [])
        number = len(state.setdefault("milestones", [])) + 1
        milestone = {**(body or {}), "number": number}
        milestone["html_url"] = f"https://github.com/{repo}/milestone/{number}"
        state["milestones"].append(milestone)
        return milestone
    if path == f"repos/{repo}/labels":
        if method == "GET":
            return state.setdefault("labels", [])
        state.setdefault("labels", []).append(body)
        return body
    if (method, path) == ("POST", f"repos/{repo}/issues"):
        number = state.get("next_number", 1)
        state["next_number"] = number + 1
        issue = {**(body or {}), "number": number, "id": number + ID_OFFSET, "blocked_by": []}
        issue["html_url"] = f"https://github.com/{repo}/issues/{number}"
        issues[str(number)] = issue
        return issue

    match = re.fullmatch(rf"repos/{re.escape(repo)}/issues/(\d+)(/dependencies/blocked_by)?", path)
    if not match or match.group(1) not in issues:
        fail("HTTP 404: Not Found")
    issue = issues[match.group(1)]
    if not match.group(2):
        if method == "PATCH":
            issue.update(body or {})
        return issue
    if method == "GET":
        return [issues[str(number)] for number in issue["blocked_by"]]

    blocker = next(
        (other for other in issues.values() if other["id"] == (body or {}).get("issue_id")), None
    )
    if blocker is None:
        fail("HTTP 404: Not Found")
    max_links = int(os.environ.get("FAKE_GH_MAX_LINKS", "1000"))
    if len(issue["blocked_by"]) < max_links:
        issue["blocked_by"].append(blocker["number"])
    return issue


if __name__ == "__main__":
    main()
