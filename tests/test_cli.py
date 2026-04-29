"""Tests for the drawio2tikz command-line interface."""

from importlib.metadata import version as package_version

from typer.testing import CliRunner

from drawio2tikz.cli import app


def test_version_option() -> None:
    """Show the installed package version without requiring an input file."""
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output == f"drawio2tikz {package_version('drawio2tikz')}\n"
