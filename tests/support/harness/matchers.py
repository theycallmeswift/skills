import fnmatch
import re
from math import inf

from .runner import RunResult


def _resolve_source(run: RunResult, on: str) -> list[str]:
    """Return the list of text sources to check against."""
    if on == "final_message":
        return [run.final_message or ""]
    if on == "stdout":
        return [run.stdout or ""]
    if on.startswith("files."):
        pattern = on[len("files.") :]
        return [
            content for path, content in run.files_written.items() if fnmatch.fnmatch(path, pattern)
        ]
    raise ValueError(f"unknown `on` target: {on!r}")


def _match_tool(trace: list[dict], needle: str) -> bool:
    return any(needle in entry.get("name", "") for entry in trace)


def _match_skill(trace: list[dict], skill: str) -> bool:
    for entry in trace:
        if entry.get("name") != "Skill":
            continue
        inv = entry.get("input", {}).get("skill", "")
        if inv == skill or inv.endswith(f":{skill}"):
            return True
    return False


class EvalResult:
    """Wraps a RunResult with assertion methods that return bool."""

    def __init__(self, run: RunResult) -> None:
        self._run = run
        self.stdout = run.stdout
        self.final_message = run.final_message
        self.files_written = run.files_written
        self.tool_trace = run.tool_trace
        self.input_tokens = run.input_tokens
        self.output_tokens = run.output_tokens
        self.exit_code = run.exit_code
        self.turn_count = run.turn_count
        self.duration_s = run.duration_s

    # --- Content matchers ---

    def matches_regex(self, pattern: str, on: str, min: int = 1, max: float = inf) -> bool:
        sources = _resolve_source(self._run, on)
        count = sum(len(re.findall(pattern, s)) for s in sources)
        return count >= min and count <= max

    def not_matches_regex(self, pattern: str, on: str) -> bool:
        return self.matches_regex(pattern, on, min=0, max=0)

    def contains(self, text: str, on: str) -> bool:
        sources = _resolve_source(self._run, on)
        return any(text in s for s in sources)

    def contains_all(self, texts: list[str], on: str) -> bool:
        sources = _resolve_source(self._run, on)
        haystack = "\n".join(sources)
        return all(t in haystack for t in texts)

    def not_contains(self, text: str, on: str) -> bool:
        return not self.contains(text, on)

    # --- Token matchers ---

    def token_usage_lte(self, n: int) -> bool:
        return (self.input_tokens + self.output_tokens) <= n

    # --- Trace matchers ---

    def tool_called(self, name: str) -> bool:
        return _match_tool(self.tool_trace, name)

    def not_tool_called(self, name: str) -> bool:
        return not _match_tool(self.tool_trace, name)

    def skill_invoked(self, name: str) -> bool:
        return _match_skill(self.tool_trace, name)

    def not_skill_invoked(self, name: str) -> bool:
        return not _match_skill(self.tool_trace, name)

    def trace_order(self, tools: list[str]) -> bool:
        names = [e.get("name", "") for e in self.tool_trace]
        cursor = 0
        for needle in tools:
            found = False
            for i in range(cursor, len(names)):
                if needle in names[i]:
                    cursor = i + 1
                    found = True
                    break
            if not found:
                return False
        return True

    def trace_count_lte(self, tool: str, n: int) -> bool:
        count = sum(1 for e in self.tool_trace if tool in e.get("name", ""))
        return count <= n

    def turn_count_lte(self, n: int) -> bool:
        return self.turn_count <= n

    # --- File matchers ---

    def file_contains(
        self, path_glob: str, text: str | None = None, regex: str | None = None
    ) -> bool:
        matches = [(p, c) for p, c in self.files_written.items() if fnmatch.fnmatch(p, path_glob)]
        if not matches:
            return False
        for _path, content in matches:
            if text is not None and text in content:
                return True
            if regex is not None and re.search(regex, content):
                return True
        return False

    def not_file_contains(
        self, path_glob: str, text: str | None = None, regex: str | None = None
    ) -> bool:
        return not self.file_contains(path_glob, text=text, regex=regex)

    # --- Rubric matcher ---

    def llm_judge(
        self,
        item: str,
        on: str | None = None,
        content: str | None = None,
        model: str | None = None,
    ) -> bool:
        """Send item + content to an LLM judge, return pass/fail.

        Pass `on` (source selector like "final_message") or `content` (raw text).
        """
        from .llm_judge import judge_rubric_item

        if content is None:
            if on is None:
                raise ValueError("llm_judge requires either `on` or `content`")
            sources = _resolve_source(self._run, on)
            content = "\n".join(sources)

        return judge_rubric_item(item, content, model=model)
