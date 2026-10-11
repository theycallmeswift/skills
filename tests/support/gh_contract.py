"""Stub GitHub API and recorder for fake-gh's cassette.

The real `gh` treats the dev host `github.localhost` as plain-HTTP GitHub at
`http://api.github.localhost/`, so routing it through an HTTP proxy on loopback lands every
request on this stub: no credentials, no internet. Run this file to re-record the cassette.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
FAKE_GH = ROOT / "evals/support/fake-gh"
CASSETTE = FAKE_GH / "cassette.txt"

HOST = "github.localhost"
REPO_URL = "https://github.com/example/orders-api"
BRANCH = "feat/payment-idempotency"
PR_FIELDS = "number,title,url,headRefName,state,isDraft,statusCheckRollup"
COMMANDS = [
    ["--version"],
    ["auth", "status"],
    ["pr", "view"],
    ["pr", "view", "--json", PR_FIELDS],
    ["pr", "status"],
    ["pr", "status", "--json", PR_FIELDS],
    ["pr", "list"],
    ["pr", "list", "--json", PR_FIELDS],
    ["pr", "checks"],
    ["pr", "checks", "--json", "name,state,bucket,link"],
]

CHECK = {
    "__typename": "CheckRun",
    "name": "ty",
    "checkSuite": {"workflowRun": {"event": "pull_request", "workflow": {"name": "CI"}}},
    "status": "COMPLETED",
    "conclusion": "FAILURE",
    "startedAt": "2026-10-08T15:10:00Z",
    "completedAt": "2026-10-08T15:10:12Z",
    "detailsUrl": f"{REPO_URL}/actions/runs/9051732",
    "isRequired": False,
}
EMPTY_PAGE = {"hasNextPage": False, "endCursor": None}
CONTEXTS = {
    "nodes": [CHECK],
    "pageInfo": EMPTY_PAGE,
    "checkRunCount": 1,
    "checkRunCountsByState": [{"state": "FAILURE", "count": 1}],
    "statusContextCount": 0,
    "statusContextCountsByState": [],
}
PULL_REQUEST = {
    "id": "PR_kwDOAAAAAM48",
    "number": 48,
    "title": "Add idempotency keys to POST /payments",
    "body": "Dedupe POST /payments on the Idempotency-Key header so retries never double-charge.",
    "url": f"{REPO_URL}/pull/48",
    "state": "OPEN",
    "isDraft": False,
    "createdAt": "2026-10-08T15:04:05Z",
    "author": {"login": "eval-user", "id": "U_kgAAAAEval", "name": "Eval User"},
    "autoMergeRequest": None,
    "maintainerCanModify": False,
    "mergeable": "MERGEABLE",
    "mergeStateStatus": "UNSTABLE",
    "additions": 64,
    "deletions": 2,
    "commits": {"totalCount": 3},
    "baseRefName": "main",
    "baseRef": {"branchProtectionRule": None},
    "headRefName": BRANCH,
    "headRepositoryOwner": {"id": "O_kgAAAAExample", "login": "example"},
    "headRepository": {"id": "R_kgAAAAOrders", "name": "orders-api"},
    "isCrossRepository": False,
    "isInMergeQueue": False,
    "isMergeQueueEnabled": False,
    "reviewDecision": None,
    "reviewRequests": {"nodes": []},
    "reviews": {"nodes": [], "pageInfo": EMPTY_PAGE, "totalCount": 0},
    "latestReviews": {"nodes": []},
    "assignees": {"nodes": [], "totalCount": 0},
    "labels": {"nodes": [], "totalCount": 0},
    "milestone": None,
    "comments": {"nodes": [], "pageInfo": EMPTY_PAGE, "totalCount": 0},
    "reactionGroups": [],
    "statusCheckRollup": {"nodes": [{"commit": {"statusCheckRollup": {"contexts": CONTEXTS}}}]},
}
TYPE_FIELDS = {
    "PullRequest": [*PULL_REQUEST],
    "StatusCheckRollupContextConnection": [*CONTEXTS],
    "WorkflowRun": ["event", "workflow"],
}


def graphql_data(query: str) -> dict[str, Any]:
    """Answer one GraphQL query from the fixture pull request, by operation name.

    Args:
        query: The GraphQL document gh sent.

    Returns:
        The response's `data` object.

    Raises:
        ValueError: if gh sent an operation the stub doesn't know, so a new query fails loudly.
    """
    operation = re.search(r"query (\w+)", query)
    name = operation.group(1) if operation else ""
    connection = {"totalCount": 1, "edges": [{"node": PULL_REQUEST}]}
    answers: dict[str, dict[str, Any]] = {
        "UserCurrent": {"viewer": {"login": "eval-user"}},
        "PullRequestForBranch": {
            "repository": {
                "pullRequests": {"nodes": [PULL_REQUEST]},
                "defaultBranchRef": {"name": "main"},
            }
        },
        "PullRequestByNumber": {"repository": {"pullRequest": PULL_REQUEST}},
        "PullRequestList": {
            "repository": {
                "pullRequests": {"totalCount": 1, "nodes": [PULL_REQUEST], "pageInfo": EMPTY_PAGE}
            }
        },
        "PullRequestStatus": {
            "repository": {"defaultBranchRef": {"name": "main"}, "pullRequests": connection},
            "viewerCreated": connection,
            "reviewRequested": {"totalCount": 0, "edges": []},
        },
        "PullRequestStatusChecks": {"node": PULL_REQUEST},
        "PullRequestProjectItems": {
            "repository": {"pullRequest": {"projectItems": {"nodes": [], "pageInfo": EMPTY_PAGE}}}
        },
    }
    if name.startswith("PullRequest_fields"):
        return {
            type_name: {"fields": [{"name": field} for field in TYPE_FIELDS[type_name]]}
            for type_name in re.findall(r"(\w+): __type", query)
        }
    if name not in answers:
        raise ValueError(f"stub has no answer for GraphQL operation {name!r}")

    return answers[name]


class Handler(BaseHTTPRequestHandler):
    """Serve gh's proxied requests for `api.github.localhost`."""

    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        """Serve the REST root gh probes for token scopes."""
        if self.path != f"http://api.{HOST}/":
            self.send_error(404)
            return

        self._send({}, {"X-Oauth-Scopes": "gist, read:org, repo, workflow"})

    def do_POST(self) -> None:
        """Serve one GraphQL request."""
        if self.path != f"http://api.{HOST}/graphql":
            self.send_error(404)
            return

        length = int(self.headers["Content-Length"])
        query = json.loads(self.rfile.read(length))["query"]
        try:
            self._send({"data": graphql_data(query)}, {})
        except ValueError as error:
            self._send({"errors": [{"message": str(error)}]}, {})

    def _send(self, body: dict[str, Any], headers: dict[str, str]) -> None:
        """Send a JSON response with an exact content length."""
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress access logging; base parameter names preserve substitutability."""
        pass


@contextmanager
def serve_stub() -> Generator[int]:
    """Serve the stub on an ephemeral loopback port and yield the port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def git(repo: Path, *args: str) -> None:
    """Run Git quietly in the recording repository."""
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )


def gh_env(home: Path, port: int) -> dict[str, str]:
    """Build an environment that isolates gh and points it at the stub.

    Args:
        home: Scratch directory for gh's config, cache, and state.
        port: The stub's loopback port.

    Returns:
        The environment for every recorded gh call.
    """
    proxy = f"http://127.0.0.1:{port}"
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GH_", "GITHUB_", "XDG_")) and "proxy" not in key.lower()
    }
    env.update(
        {
            "HOME": str(home),
            "GH_CONFIG_DIR": str(home / "gh"),
            "XDG_CACHE_HOME": str(home / "cache"),
            "XDG_STATE_HOME": str(home / "state"),
            "XDG_DATA_HOME": str(home / "data"),
            "GH_HOST": HOST,
            "GH_NO_UPDATE_NOTIFIER": "1",
            "GH_PROMPT_DISABLED": "1",
            "NO_COLOR": "1",
            # https would leave the machine; aim it at the stub too so any such call fails.
            "HTTP_PROXY": proxy,
            "HTTPS_PROXY": proxy,
        }
    )
    return env


def record() -> str:
    """Run every command in COMMANDS through the real gh and render the cassette.

    Returns:
        The cassette text: per command, a `$ gh ...` line, a `? <exit code>` line, then its
        stdout, with the stub's host and config path scrubbed to what a real setup shows.
    """
    cassette = "# Recorded from the real gh by tests/support/gh_contract.py. See README.md.\n"
    with tempfile.TemporaryDirectory() as scratch, serve_stub() as port:
        home = Path(scratch)
        (home / "gh").mkdir()
        (home / "gh/hosts.yml").write_text(
            f"{HOST}:\n    oauth_token: gho_{'0' * 36}\n    user: eval-user\n"
            "    git_protocol: https\n"
        )
        repo = home / "repo"
        git(home, "init", "-q", "-b", "main", str(repo))
        git(repo, "commit", "-q", "--allow-empty", "-m", "init")
        git(repo, "checkout", "-q", "-b", BRANCH)
        git(repo, "remote", "add", "origin", f"https://{HOST}/example/orders-api.git")
        git(repo, "update-ref", f"refs/remotes/origin/{BRANCH}", "HEAD")
        git(repo, "branch", "-q", f"--set-upstream-to=origin/{BRANCH}")

        for command in COMMANDS:
            result = subprocess.run(
                ["gh", *command],
                cwd=repo,
                env=gh_env(home, port),
                capture_output=True,
                text=True,
                timeout=30,
            )
            stdout = result.stdout.replace(str(home / "gh"), "/root/.config/gh")
            stdout = stdout.replace(HOST, "github.com")
            if stdout and not stdout.endswith("\n"):
                raise ValueError(f"gh {' '.join(command)}: stdout lacks a final newline")
            cassette += f"$ gh {' '.join(command)}\n? {result.returncode}\n{stdout}"

    return cassette


if __name__ == "__main__":
    CASSETTE.write_text(record())
