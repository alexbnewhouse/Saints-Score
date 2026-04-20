"""Tests for saints_score.cli — Click CLI interface."""

from click.testing import CliRunner

from saints_score.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Saints Score" in result.output
    assert "ingest" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0


def test_cli_ingest_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["ingest", "--help"])
    assert result.exit_code == 0
    assert "--config" in result.output


def test_cli_mentions_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["mentions", "--help"])
    assert result.exit_code == 0


def test_cli_drift_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["drift", "--help"])
    assert result.exit_code == 0
    assert "drift" in result.output.lower()


def test_cli_run_all_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["run-all", "--help"])
    assert result.exit_code == 0
