from pathlib import Path
from tests.support.harness.discovery import load_eval_file, EvalSuite, EvalCase

FIXTURES = Path(__file__).parent.parent / "fixtures"

def test_load_skill_eval_file():
    suite = load_eval_file(FIXTURES / "sample-skill-eval.json", kind="skill")
    assert isinstance(suite, EvalSuite)
    assert suite.name == "ghostwrite"
    assert suite.kind == "skill"
    assert len(suite.cases) == 1
    case = suite.cases[0]
    assert case.id == "sponsor-email"
    assert case.prompt.startswith("Rewrite this")
    assert case.files == []
    assert case.assertions == [{"text": "Output is short"}]
    assert case.grader_model is None
    assert case.cleanup == []

def test_load_core_eval_file():
    suite = load_eval_file(FIXTURES / "sample-core-eval.json", kind="core")
    assert suite.kind == "core"
    case = suite.cases[0]
    assert case.grader_model == "claude-haiku-4-5-20251001"
    assert case.cleanup == ["tmp/fake-repo"]

def test_discover_walks_tests_tree(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )

    from tests.support.harness.discovery import discover_suites
    suites = discover_suites(tmp_path / "tests")
    assert len(suites) == 2
    by_name = {s.name: s for s in suites}
    assert by_name["ghostwrite"].kind == "skill"
    assert by_name["no-ai-attribution"].kind == "core"

def test_discover_filters_by_name(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )

    from tests.support.harness.discovery import discover_suites
    suites = discover_suites(tmp_path / "tests", names=["ghostwrite"])
    assert len(suites) == 1
    assert suites[0].name == "ghostwrite"
