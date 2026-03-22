"""Smoke tests — verify the CLI entry points respond to --help."""

from __future__ import annotations

import sys

from click.testing import CliRunner


class TestCLISmoke:
    """Verify ghps --help and ghps search --help return exit code 0."""

    def setup_method(self):
        sys.modules.pop("ghps.cli", None)

    def teardown_method(self):
        sys.modules.pop("ghps.cli", None)

    def test_ghps_help_returns_zero(self):
        from ghps.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0, f"ghps --help failed: {result.output}"
        assert "search" in result.output

    def test_ghps_search_help_returns_zero(self):
        from ghps.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])

        assert result.exit_code == 0, f"ghps search --help failed: {result.output}"
        assert "query" in result.output.lower() or "QUERY" in result.output
