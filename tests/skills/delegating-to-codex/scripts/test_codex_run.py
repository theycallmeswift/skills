"""Tests for codex_run.py.

Pure logic (argv building, state-dir lookup, prompt assembly, usage parsing, pruning,
diff inlining) is tested directly. The job lifecycle and guards run against a fake
`codex` on PATH that logs its argv, stdin and cwd and emits canned JSONL. No test ever
calls a real `codex`.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import codex_run as cr
import pytest

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
SCHEMA = str(cr.ASSETS / "review-output.schema.json")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [*GIT, "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


FAKE_CODEX = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys, time
    args = sys.argv[1:]
    if args[:2] == ["login", "status"]:
        rc = int(os.environ.get("FAKE_CODEX_LOGIN_RC", "0"))
        print("Logged in" if rc == 0 else "Not logged in", file=sys.stderr)
        sys.exit(rc)
    stdin = sys.stdin.read()
    with open(os.environ["FAKE_CODEX_LOG"], "a") as f:
        rec = {{"argv": args, "stdin": stdin, "cwd": os.getcwd(), "pid": os.getpid()}}
        f.write(json.dumps(rec) + "\\n")
    thread = os.environ.get("FAKE_THREAD_ID", "thread-abc")
    print(json.dumps({{"type": "thread.started", "thread_id": thread}}), flush=True)
    time.sleep(float(os.environ.get("FAKE_CODEX_SLEEP", "0")))
    if os.environ.get("FAKE_CODEX_EDIT"):
        open(os.environ["FAKE_CODEX_EDIT"], "w").write("edited\\n")
    out = args[args.index("-o") + 1]
    open(out, "w").write(os.environ.get("FAKE_LAST", "STATUS: DONE\\n"))
    usage = {{"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 7,
              "reasoning_output_tokens": 3}}
    print(json.dumps({{"type": "turn.completed", "usage": usage}}), flush=True)
    sys.exit(int(os.environ.get("FAKE_CODEX_RC", "0")))
    """
)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A clean git repo, a fake codex on PATH, and an isolated state dir."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "codex"
    fake.write_text(FAKE_CODEX.format(python=sys.executable))
    fake.chmod(0o755)
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "a.py").write_text("x = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "init")
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "brief.md").write_text("Make x equal 2.\n")
    (inputs / "risks.md").write_text("R1: x must stay an int.\n")
    log = tmp_path / "codex.log"
    for var in (
        "CODEX_THREAD_ID",
        "CLAUDE_CODE_SESSION_ID",
        "HERMES_HOME",
        "XDG_STATE_HOME",
        "PROJECT_ROOT",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "state"))
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CODEX_LOG", str(log))
    monkeypatch.chdir(repo)

    class Env:
        pass

    e = Env()
    e.tmp, e.repo, e.inputs, e.log, e.bindir = tmp_path, repo, inputs, log, bindir
    e.brief, e.risks = str(inputs / "brief.md"), str(inputs / "risks.md")
    return e


def calls(e) -> list[dict]:
    if not e.log.exists():
        return []
    return [json.loads(line) for line in e.log.read_text().splitlines()]


def job_dir(e, job_id: str) -> Path:
    return cr.jobs_dir(os.environ, cr.resolve_worktree(str(e.repo))) / job_id


def meta(e, job_id: str) -> dict:
    return json.loads((job_dir(e, job_id) / "meta.json").read_text())


def wait_done(e, job_id: str, timeout: float = 15) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        m = meta(e, job_id)
        if m["status"] != "running":
            return m
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} still running")


def start(capsys, *args: str) -> tuple[int, str, str]:
    rc = cr.main(["start", *args])
    out = capsys.readouterr()
    return rc, out.out, out.err


def started_id(out: str) -> str:
    for line in out.splitlines():
        if line.startswith("job "):
            return line.split()[1]
    raise AssertionError(f"no job id in: {out!r}")


# ---------------------------------------------------------------------------
# build_argv


WT = Path("/wt")
JD = Path("/state/job")


def test_argv_implement_minimal():
    assert cr.build_argv("implement", worktree=WT, job_dir=JD, effort="high") == [
        "codex", "exec", "--sandbox", "workspace-write", "--cd", "/wt", "--json",
        "--strict-config", "-c", "model_reasoning_effort=high",
        "-o", "/state/job/last.md", "-",
    ]  # fmt: skip


def test_argv_implement_all_flags():
    argv = cr.build_argv(
        "implement", worktree=WT, job_dir=JD, effort="xhigh", model="m1", tier="flex",
        network=True,
    )  # fmt: skip
    assert argv == [
        "codex", "exec", "--sandbox", "workspace-write", "--cd", "/wt", "--json",
        "--strict-config", "-c", "model_reasoning_effort=xhigh", "-c", "service_tier=flex",
        "-m", "m1", "-c", "sandbox_workspace_write.network_access=true",
        "-o", "/state/job/last.md", "-",
    ]  # fmt: skip


def test_argv_resume():
    argv = cr.build_argv(
        "implement", worktree=WT, job_dir=JD, effort="low", thread_id="T1", tier="fast",
        model="m2", network=True,
    )  # fmt: skip
    assert argv == [
        "codex", "exec", "resume", "T1", "--json", "--strict-config",
        "-c", 'sandbox_mode="workspace-write"', "-c", "model_reasoning_effort=low",
        "-c", "service_tier=fast", "-m", "m2",
        "-c", "sandbox_workspace_write.network_access=true",
        "-o", "/state/job/last.md", "-",
    ]  # fmt: skip


def test_argv_resume_minimal_has_no_cd_or_sandbox_flag():
    argv = cr.build_argv("implement", worktree=WT, job_dir=JD, effort="low", thread_id="T1")
    assert "--cd" not in argv and "--sandbox" not in argv
    assert argv[:4] == ["codex", "exec", "resume", "T1"]


def test_argv_review_minimal():
    assert cr.build_argv("review", worktree=WT, job_dir=JD, effort="low") == [
        "codex", "exec", "--sandbox", "read-only", "--ephemeral", "--cd", "/wt", "--json",
        "--strict-config", "-c", "model_reasoning_effort=low",
        "--output-schema", SCHEMA, "-o", "/state/job/last.md", "-",
    ]  # fmt: skip


def test_argv_review_with_model_and_tier():
    argv = cr.build_argv("review", worktree=WT, job_dir=JD, effort="medium", model="m", tier="t")
    assert argv == [
        "codex", "exec", "--sandbox", "read-only", "--ephemeral", "--cd", "/wt", "--json",
        "--strict-config", "-c", "model_reasoning_effort=medium", "-c", "service_tier=t",
        "-m", "m", "--output-schema", SCHEMA, "-o", "/state/job/last.md", "-",
    ]  # fmt: skip


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "implement"},
        {"mode": "implement", "thread_id": "T", "network": True},
        {"mode": "review"},
    ],
)
def test_argv_never_escalates(kwargs):
    argv = cr.build_argv(worktree=WT, job_dir=JD, effort="high", **kwargs)
    joined = " ".join(argv)
    assert "--ignore-user-config" not in argv
    assert "--add-dir" not in argv
    assert "--dangerously" not in joined


def test_argv_review_rejects_network_and_resume():
    with pytest.raises(ValueError):
        cr.build_argv("review", worktree=WT, job_dir=JD, effort="low", network=True)
    with pytest.raises(ValueError):
        cr.build_argv("review", worktree=WT, job_dir=JD, effort="low", thread_id="T")


# ---------------------------------------------------------------------------
# state_root / jobs_dir


def test_state_root_prefers_claude_plugin_data():
    env = {
        "CLAUDE_PLUGIN_DATA": "/cpd",
        "HERMES_HOME": "/hh",
        "XDG_STATE_HOME": "/xdg",
        "HOME": "/home/u",
    }
    assert cr.state_root(env) == Path("/cpd")


def test_state_root_hermes_then_xdg_then_home():
    assert cr.state_root({"HERMES_HOME": "/hh", "XDG_STATE_HOME": "/x"}) == Path(
        "/hh/mechaswift"
    )
    assert cr.state_root({"XDG_STATE_HOME": "/x", "HOME": "/h"}) == Path("/x/mechaswift")
    assert cr.state_root({"HOME": "/h"}) == Path("/h/.local/state/mechaswift")


def test_state_root_ignores_empty_values():
    assert cr.state_root({"CLAUDE_PLUGIN_DATA": "", "HERMES_HOME": "", "HOME": "/h"}) == Path(
        "/h/.local/state/mechaswift"
    )


def test_jobs_dir_keyed_by_worktree(tmp_path):
    wt = tmp_path / "my-repo"
    wt.mkdir()
    digest = hashlib.sha256(str(wt.resolve()).encode()).hexdigest()[:16]
    d = cr.jobs_dir({"CLAUDE_PLUGIN_DATA": "/cpd"}, wt)
    assert d == Path("/cpd/codex-jobs") / f"my-repo-{digest}"
    assert cr.jobs_dir({"CLAUDE_PLUGIN_DATA": "/cpd"}, wt) == d
    other = tmp_path / "other" / "my-repo"
    other.mkdir(parents=True)
    assert cr.jobs_dir({"CLAUDE_PLUGIN_DATA": "/cpd"}, other) != d


def test_job_id_format():
    import re

    jid = cr.new_job_id("review")
    assert re.fullmatch(r"\d{8}-\d{6}-review-[0-9a-f]{4}", jid)


# ---------------------------------------------------------------------------
# prompt assembly


def test_prompt_implement_section_order():
    p = cr.build_prompt(
        "implement",
        template="TEMPLATE",
        brief="BRIEF TEXT",
        rules="RULES TEXT",
        context="CTX",
        risks="RISKS",
    )
    heads = [
        "=== TASK TEMPLATE ===",
        "=== RULES ===",
        "=== BRIEF ===",
        "=== CONTEXT ===",
        "=== NAMED RISKS ===",
    ]
    idx = [p.index(h) for h in heads]
    assert idx == sorted(idx)
    assert "TEMPLATE" in p and "BRIEF TEXT" in p and "RULES TEXT" in p
    assert "IMPLEMENTER REPORT" not in p and "=== DIFF ===" not in p


def test_prompt_optional_sections_omitted():
    p = cr.build_prompt("implement", template="T", brief="B")
    assert "=== RULES ===" not in p
    assert "=== CONTEXT ===" not in p
    assert "=== NAMED RISKS ===" not in p


def test_prompt_review_section_order():
    p = cr.build_prompt(
        "review",
        template="T",
        brief="B",
        rules="R",
        context="C",
        report="REP",
        risks="RISK",
        diff="DIFF",
    )
    heads = [
        "=== TASK TEMPLATE ===",
        "=== RULES ===",
        "=== BRIEF ===",
        "=== CONTEXT ===",
        "=== IMPLEMENTER REPORT ===",
        "=== NAMED RISKS ===",
        "=== DIFF ===",
    ]
    idx = [p.index(h) for h in heads]
    assert idx == sorted(idx)


def test_resume_prompt_is_just_brief():
    p = cr.build_resume_prompt("Fix finding 1.\n")
    assert "Fix finding 1." in p
    assert "=== BRIEF ===" in p
    assert "=== TASK TEMPLATE ===" not in p


def test_diff_inlined_when_small():
    info = cr.DiffInfo(
        label="uncommitted changes",
        files=["a.py", "b.py"],
        text="diff --git a/a.py b/a.py\n+x\n",
        commands=["git diff HEAD"],
    )
    s = cr.render_diff_section(info)
    assert "diff --git a/a.py b/a.py" in s
    assert "a.py" in s and "b.py" in s


def test_diff_not_inlined_over_two_files():
    info = cr.DiffInfo(
        label="branch vs main",
        files=["a", "b", "c"],
        text="diff --git SECRET-DIFF-BODY\n",
        commands=["git diff abc123"],
    )
    s = cr.render_diff_section(info)
    assert "SECRET-DIFF-BODY" not in s
    assert "git diff abc123" in s


def test_diff_not_inlined_over_size_limit():
    body = "+" + "y" * (256 * 1024) + "\n"
    info = cr.DiffInfo(label="l", files=["a"], text=body, commands=["git diff m"])
    s = cr.render_diff_section(info)
    assert len(s) < 10_000
    assert "git diff m" in s


def test_diff_at_size_limit_is_inlined():
    body = "z" * (256 * 1024)
    info = cr.DiffInfo(label="l", files=["a"], text=body, commands=["git diff m"])
    assert body in cr.render_diff_section(info)


# ---------------------------------------------------------------------------
# usage parsing


def test_parse_events_last_turn_completed_wins():
    stream = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "T9"}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 10,
                        "cached_input_tokens": 4,
                        "output_tokens": 2,
                        "reasoning_output_tokens": 1,
                    },
                }
            ),
        ]
    )
    thread, usage = cr.parse_events(stream)
    assert thread == "T9"
    assert usage == {
        "input_tokens": 10,
        "cached_input_tokens": 4,
        "output_tokens": 2,
        "reasoning_output_tokens": 1,
    }


def test_parse_events_truncated_stream():
    stream = json.dumps({"type": "thread.started", "thread_id": "T"}) + '\n{"type": "turn.comp'
    assert cr.parse_events(stream) == ("T", None)
    assert cr.parse_events("") == (None, None)
    assert cr.parse_events("not json\n[1,2]\n") == (None, None)


def test_format_usage():
    u = {
        "input_tokens": 10,
        "cached_input_tokens": 4,
        "output_tokens": 2,
        "reasoning_output_tokens": 1,
    }
    assert cr.format_usage(u) == "tokens: in 10 (cached 4), out 2, reasoning 1"
    assert cr.format_usage(None) == "tokens: unavailable"


# ---------------------------------------------------------------------------
# pruning


def test_prune_keeps_newest(tmp_path):
    for i in range(60):
        d = tmp_path / f"job{i:02d}"
        d.mkdir()
        (d / "meta.json").write_text(json.dumps({"created_at": f"2026-01-01T00:00:{i:02d}"}))
    cr.prune_jobs(tmp_path, keep=50)
    left = sorted(p.name for p in tmp_path.iterdir())
    assert len(left) == 50
    assert left[0] == "job10" and left[-1] == "job59"


def test_prune_noop_under_limit(tmp_path):
    for i in range(3):
        (tmp_path / f"j{i}").mkdir()
    cr.prune_jobs(tmp_path, keep=50)
    assert len(list(tmp_path.iterdir())) == 3


# ---------------------------------------------------------------------------
# guards


def test_start_requires_effort(env):
    with pytest.raises(SystemExit) as exc:
        cr.main(["start", "implement", "--brief", env.brief])
    assert exc.value.code == 2


def test_start_rejects_bad_effort(env):
    with pytest.raises(SystemExit):
        cr.main(["start", "implement", "--effort", "ultra", "--brief", env.brief])


def test_network_only_for_implement(env, capsys):
    rc, _, err = start(capsys, "review", "--effort", "low", "--brief", env.brief, "--network")
    assert rc == 2 and "--network" in err
    assert calls(env) == []


def test_resume_only_for_implement(env, capsys):
    rc, _, err = start(capsys, "review", "--effort", "low", "--brief", env.brief, "--resume", "x")
    assert rc == 2 and "--resume" in err


def test_brief_required(env, capsys):
    rc, _, err = start(capsys, "implement", "--effort", "high")
    assert rc == 2 and "--brief" in err


def test_missing_input_file_named(env, capsys):
    rc, _, err = start(
        capsys, "implement", "--effort", "high", "--brief", env.brief, "--risks", "nope.md"
    )
    assert rc == 2 and "nope.md" in err
    assert calls(env) == []


def test_not_a_git_repo(env, capsys, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    rc, _, err = start(
        capsys, "implement", "--effort", "high", "--brief", env.brief, "--cd", str(plain)
    )
    assert rc == 2 and "git" in err.lower()


def test_preflight_ok(env, capsys):
    assert cr.main(["preflight"]) == 0


def test_preflight_codex_missing(env, capsys, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert cr.main(["preflight"]) == 3
    assert "codex" in capsys.readouterr().err


def test_preflight_logged_out(env, capsys, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_LOGIN_RC", "1")
    assert cr.main(["preflight"]) == 3
    assert "codex login" in capsys.readouterr().err


def test_preflight_inside_codex(env, capsys, monkeypatch):
    monkeypatch.setenv("CODEX_THREAD_ID", "abc")
    assert cr.main(["preflight"]) == 3
    assert "already running inside Codex" in capsys.readouterr().err


def test_start_runs_preflight(env, capsys, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_LOGIN_RC", "1")
    rc, _, _ = start(capsys, "implement", "--effort", "high", "--brief", env.brief)
    assert rc == 3
    assert calls(env) == []


def test_implement_refuses_dirty_worktree(env, capsys):
    (env.repo / "a.py").write_text("x = 5\n")
    rc, _, err = start(capsys, "implement", "--effort", "high", "--brief", env.brief)
    assert rc == 2 and "uncommitted" in err
    assert calls(env) == []


# ---------------------------------------------------------------------------
# lifecycle against the fake codex


def test_implement_wait_end_to_end(env, capsys, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")
    rc, out, _ = start(
        capsys, "implement", "--effort", "high", "--brief", env.brief, "--risks", env.risks,
        "--wait",
    )  # fmt: skip
    assert rc == 0
    jid = started_id(out)
    assert "STATUS: DONE" in out
    assert "tokens: in 100 (cached 40), out 7, reasoning 3" in out
    m = meta(env, jid)
    assert m["status"] == "completed" and m["exit_code"] == 0
    assert m["thread_id"] == "thread-abc"
    assert m["session_id"] == "sess-1"
    assert m["mode"] == "implement"
    assert m["usage"]["output_tokens"] == 7
    assert m["finished_at"]
    (call,) = calls(env)
    assert call["argv"][:5] == ["exec", "--sandbox", "workspace-write", "--cd", str(env.repo)]
    assert "model_reasoning_effort=high" in call["argv"]
    assert Path(call["cwd"]).resolve() == env.repo.resolve()
    assert "Make x equal 2." in call["stdin"]
    assert "R1: x must stay an int." in call["stdin"]
    assert "=== TASK TEMPLATE ===" in call["stdin"]
    jd = job_dir(env, jid)
    for name in ("prompt.md", "events.jsonl", "stderr.log", "last.md", "meta.json"):
        assert (jd / name).exists(), name
    assert not str(jd).startswith(str(env.repo))


def test_background_start_then_status_then_result(env, capsys, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "1.5")
    rc, out, _ = start(capsys, "implement", "--effort", "high", "--brief", env.brief)
    assert rc == 0
    jid = started_id(out)
    assert str(job_dir(env, jid)) in out
    time.sleep(0.3)
    assert cr.main(["status"]) == 0
    status_out = capsys.readouterr().out
    assert jid in status_out and "running" in status_out
    assert cr.main(["result", jid]) == 4
    assert "still running" in capsys.readouterr().out
    wait_done(env, jid)
    assert cr.main(["result", "last"]) == 0
    res = capsys.readouterr().out
    assert "completed" in res and "STATUS: DONE" in res and "tokens: in 100" in res


def test_result_json(env, capsys):
    rc, out, _ = start(capsys, "implement", "--effort", "low", "--brief", env.brief, "--wait")
    jid = started_id(out)
    assert cr.main(["result", jid, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["id"] == jid
    assert data["last_message"].startswith("STATUS: DONE")
    assert data["usage"]["input_tokens"] == 100


def test_failed_job(env, capsys, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_RC", "7")
    rc, out, _ = start(capsys, "implement", "--effort", "low", "--brief", env.brief, "--wait")
    assert rc == 1
    m = meta(env, started_id(out))
    assert m["status"] == "failed" and m["exit_code"] == 7


def test_result_no_usage(env, capsys, monkeypatch):
    rc, out, _ = start(capsys, "implement", "--effort", "low", "--brief", env.brief, "--wait")
    jid = started_id(out)
    jd = job_dir(env, jid)
    m = json.loads((jd / "meta.json").read_text())
    m["usage"] = None
    (jd / "meta.json").write_text(json.dumps(m))
    cr.main(["result", jid])
    assert "tokens: unavailable" in capsys.readouterr().out


def test_result_unknown_job(env, capsys):
    assert cr.main(["result", "nope"]) == 2


def test_cancel_kills_and_keeps_edits(env, capsys, monkeypatch):
    edit = env.repo / "new.txt"
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "30")
    rc, out, _ = start(capsys, "implement", "--effort", "high", "--brief", env.brief)
    jid = started_id(out)
    deadline = time.time() + 10
    while time.time() < deadline and not (calls(env) and meta(env, jid).get("pid")):
        time.sleep(0.05)
    edit.write_text("partial edit\n")
    codex_pid = calls(env)[0]["pid"]
    assert cr.main(["cancel", jid]) == 0
    msg = capsys.readouterr().out
    assert "git status" in msg
    assert meta(env, jid)["status"] == "cancelled"
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(codex_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(codex_pid, signal.SIGKILL)
        raise AssertionError("codex process survived cancel")
    time.sleep(0.2)
    assert meta(env, jid)["status"] == "cancelled"
    assert edit.read_text() == "partial edit\n"


def test_status_marks_dead_pid_failed(env, capsys):
    rc, out, _ = start(capsys, "implement", "--effort", "low", "--brief", env.brief, "--wait")
    jid = started_id(out)
    jd = job_dir(env, jid)
    m = json.loads((jd / "meta.json").read_text())
    dead = subprocess.Popen(["true"])
    dead.wait()
    m.update(status="running", pid=dead.pid, finished_at=None)
    (jd / "meta.json").write_text(json.dumps(m))
    cr.main(["status"])
    capsys.readouterr()
    assert meta(env, jid)["status"] == "failed"


def test_status_filters_by_session(env, capsys, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    _, out1, _ = start(capsys, "implement", "--effort", "low", "--brief", env.brief, "--wait")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s2")
    _, out2, _ = start(capsys, "implement", "--effort", "low", "--brief", env.brief, "--wait")
    a, b = started_id(out1), started_id(out2)
    cr.main(["status"])
    shown = capsys.readouterr().out
    assert b in shown and a not in shown
    cr.main(["status", "--all"])
    shown = capsys.readouterr().out
    assert a in shown and b in shown
    cr.main(["status", "--all", "--json"])
    ids = [j["id"] for j in json.loads(capsys.readouterr().out)]
    assert ids == [b, a]


def test_resume_uses_recorded_thread(env, capsys, monkeypatch):
    monkeypatch.setenv("FAKE_THREAD_ID", "thread-first")
    _, out, _ = start(capsys, "implement", "--effort", "high", "--brief", env.brief, "--wait")
    first = started_id(out)
    (env.repo / "a.py").write_text("x = 2\n")  # dirty is fine on resume
    fixes = env.inputs / "fixes.md"
    fixes.write_text("Fix finding 1: add a test.\n")
    rc, out, _ = start(
        capsys, "implement", "--resume", first, "--effort", "medium", "--brief", str(fixes),
        "--wait",
    )  # fmt: skip
    assert rc == 0
    second = started_id(out)
    call = calls(env)[-1]
    assert call["argv"][:3] == ["exec", "resume", "thread-first"]
    assert 'sandbox_mode="workspace-write"' in call["argv"]
    assert Path(call["cwd"]).resolve() == env.repo.resolve()
    assert "Fix finding 1" in call["stdin"]
    assert "=== TASK TEMPLATE ===" not in call["stdin"]
    assert meta(env, second)["resumed_from"] == first


def test_resume_without_thread_id(env, capsys):
    _, out, _ = start(capsys, "implement", "--effort", "high", "--brief", env.brief, "--wait")
    first = started_id(out)
    jd = job_dir(env, first)
    m = json.loads((jd / "meta.json").read_text())
    m["thread_id"] = None
    (jd / "meta.json").write_text(json.dumps(m))
    n = len(calls(env))
    rc, _, err = start(
        capsys, "implement", "--resume", first, "--effort", "high", "--brief", env.brief
    )
    assert rc == 2 and "thread" in err
    assert len(calls(env)) == n


def test_start_prunes_old_jobs(env, capsys):
    jobs = cr.jobs_dir(os.environ, cr.resolve_worktree(str(env.repo)))
    for i in range(55):
        d = jobs / f"20000101-0000{i:02d}-implement-0000"
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"created_at": f"2000-01-01T00:00:{i:02d}"}))
    _, out, _ = start(capsys, "implement", "--effort", "low", "--brief", env.brief, "--wait")
    remaining = list(jobs.iterdir())
    assert len(remaining) == 50
    assert started_id(out) in {p.name for p in remaining}


# ---------------------------------------------------------------------------
# review against the fake codex


def test_review_uncommitted_inlines_small_diff(env, capsys):
    (env.repo / "a.py").write_text("x = 2\n")
    (env.repo / "b.py").write_text("y = 1\n")
    report = env.inputs / "report.md"
    report.write_text("STATUS: DONE, all tests pass\n")
    rc, out, _ = start(
        capsys, "review", "--effort", "low", "--brief", env.brief, "--report", str(report),
        "--risks", env.risks, "--wait",
    )  # fmt: skip
    assert rc == 0
    call = calls(env)[-1]
    assert call["argv"][:5] == ["exec", "--sandbox", "read-only", "--ephemeral", "--cd"]
    assert "--output-schema" in call["argv"]
    stdin = call["stdin"]
    assert "=== IMPLEMENTER REPORT ===" in stdin and "all tests pass" in stdin
    assert "=== DIFF ===" in stdin
    assert "+x = 2" in stdin
    assert "b.py" in stdin
    assert stdin.index("=== NAMED RISKS ===") < stdin.index("=== DIFF ===")


def test_review_branch_large_diff_gives_command(env, capsys):
    base = git(env.repo, "rev-parse", "HEAD").strip()
    git(env.repo, "checkout", "-q", "-b", "feature")
    for name in ("c.py", "d.py", "e.py"):
        (env.repo / name).write_text(f"# {name} BODYMARK\n")
    git(env.repo, "add", ".")
    git(env.repo, "commit", "-q", "-m", "feature")
    rc, _, _ = start(capsys, "review", "--effort", "low", "--brief", env.brief, "--wait")
    assert rc == 0
    stdin = calls(env)[-1]["stdin"]
    assert f"git diff {base}" in stdin
    assert "BODYMARK" not in stdin
    assert "c.py" in stdin


def test_review_explicit_base(env, capsys):
    first = git(env.repo, "rev-parse", "HEAD").strip()
    (env.repo / "a.py").write_text("x = 3\n")
    git(env.repo, "commit", "-q", "-am", "second")
    rc, _, _ = start(
        capsys, "review", "--effort", "low", "--brief", env.brief, "--base", first, "--wait"
    )
    assert rc == 0
    assert "+x = 3" in calls(env)[-1]["stdin"]


def test_review_nothing_to_review(env, capsys):
    rc, _, err = start(capsys, "review", "--effort", "low", "--brief", env.brief)
    assert rc == 2 and "nothing to review" in err
    assert calls(env) == []


# ---------------------------------------------------------------------------
# input files written inside the worktree


def test_implement_ignores_its_own_input_files_in_worktree(env, capsys):
    notes = env.repo / "notes"
    notes.mkdir()
    (notes / "brief.md").write_text("Make x equal 2.\n")
    rc, _, err = start(
        capsys, "implement", "--effort", "high", "--brief", str(notes / "brief.md"), "--wait"
    )
    assert rc == 0, err
    assert len(calls(env)) == 1


def test_implement_still_refuses_other_untracked_files(env, capsys):
    (env.repo / "brief.md").write_text("Make x equal 2.\n")
    (env.repo / "stray.py").write_text("junk\n")
    rc, _, err = start(capsys, "implement", "--effort", "high", "--brief", "brief.md")
    assert rc == 2 and "stray.py" in err
    assert calls(env) == []


def test_review_without_base_ignores_input_files_when_choosing_scope(env, capsys):
    base = git(env.repo, "rev-parse", "HEAD").strip()
    git(env.repo, "checkout", "-q", "-b", "feature")
    (env.repo / "a.py").write_text("x = 9\n")
    git(env.repo, "commit", "-q", "-am", "feature")
    (env.repo / "brief.md").write_text("Review it.\n")
    rc, _, err = start(capsys, "review", "--effort", "low", "--brief", "brief.md", "--wait")
    assert rc == 0, err
    stdin = calls(env)[-1]["stdin"]
    assert "merge-base with main" in stdin and base in stdin
    assert "+x = 9" in stdin
    assert "brief.md (untracked)" not in stdin
