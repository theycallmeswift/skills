from click.testing import CliRunner

from ledger.cli import main


def test_report_prints_the_balance(sample_store):
    result = CliRunner().invoke(main, ["report", "checking"])
    assert result.output == "checking: 120.50\n"
