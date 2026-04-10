from tests.support.harness.reporter import EvalReporter


def _make_report(nodeid, passed, duration=1.0):
    """Create a minimal mock test report."""

    class FakeReport:
        def __init__(self):
            self.nodeid = nodeid
            self.when = "call"
            self.passed = passed
            self.failed = not passed
            self.duration = duration
            self.longreprtext = "" if passed else "AssertionError: test failed"

    return FakeReport()


def test_reporter_groups_by_module():
    r = EvalReporter(verbose=False)
    r.record_result(
        _make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_greeting", True)
    )
    r.record_result(
        _make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_sign_off", False)
    )
    r.record_result(
        _make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_numbers", True)
    )

    rows = r.build_table_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["skill"] == "ghostwrite"
    assert row["test"] == "test_sponsor_email"
    assert row["passed"] == 2
    assert row["total"] == 3


def test_reporter_handles_core_tests():
    r = EvalReporter(verbose=False)
    r.record_result(
        _make_report("tests/core/test_skill_triggers.py::test_ghostwrite_trigger", True)
    )
    r.record_result(_make_report("tests/core/test_skill_triggers.py::test_scope_trigger", True))

    rows = r.build_table_rows()
    assert len(rows) == 1
    assert rows[0]["skill"] == "core"
    assert rows[0]["test"] == "test_skill_triggers"


def test_reporter_computes_totals():
    r = EvalReporter(verbose=False)
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_a", True))
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_b", False))
    r.record_result(_make_report("tests/skills/summarize/test_devto_article.py::test_c", True))

    totals = r.compute_totals()
    assert totals["passed"] == 2
    assert totals["total"] == 3


def test_reporter_format_output():
    r = EvalReporter(verbose=False)
    r.record_result(
        _make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_a", True, 15.2)
    )
    r.record_result(
        _make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_b", False, 15.2)
    )

    output = r.format_table()
    assert "ghostwrite" in output
    assert "test_sponsor_email" in output
    assert "1/2" in output
