from unittest.mock import MagicMock, patch

from rich.panel import Panel

from veildata.diagnostics import print_error


def test_print_error_structure():
    """Test that print_error constructs the Panel correctly."""
    mock_console = MagicMock()

    print_error(
        mock_console,
        title="Test Error",
        message="Something went wrong",
        suggestion="Try fixing it",
    )

    # Verify console.print was called
    mock_console.print.assert_called_once()

    # Get the argument passed to print (should be a Panel)
    arg = mock_console.print.call_args[0][0]
    assert isinstance(arg, Panel)
    assert "Test Error" in arg.title

    # We can't easily check the content of the Text object inside the Panel
    # without inspecting private attributes or rendering, but we can check basic properties.
    assert arg.border_style == "red"


@patch("veildata.engine.build_masker")
def test_cli_config_missing_error(mock_build_masker):
    """Test that CLI catches ConfigMissingError and prints formatted error."""
    from typer.testing import CliRunner

    from veildata.cli import app
    from veildata.exceptions import ConfigMissingError

    runner = CliRunner()

    # Simulate ConfigMissingError
    mock_build_masker.side_effect = ConfigMissingError("Config file not found")

    # We need to patch the console object in cli.py to verify print_error calls
    with patch("veildata.cli.console") as mock_console:
        result = runner.invoke(app, ["mask", "input.txt", "--config", "missing.yaml"])

        assert result.exit_code == 1

        # Verify print_error logic (via console.print)
        # Since print_error calls console.print(Panel(...))
        assert mock_console.print.called
        args = mock_console.print.call_args[0]
        assert isinstance(args[0], Panel)
        assert "Configuration Error" in args[0].title


@patch("veildata.engine.build_masker")
def test_cli_os_error(mock_build_masker):
    """Test that CLI catches OSError (model download declined) and prints formatted error."""
    from typer.testing import CliRunner

    from veildata.cli import app

    runner = CliRunner()

    # Simulate OSError
    mock_build_masker.side_effect = OSError("Model download declined")

    with patch("veildata.cli.console") as mock_console:
        result = runner.invoke(app, ["mask", "input.txt"])

        assert result.exit_code == 1

        assert mock_console.print.called
        args = mock_console.print.call_args[0]
        assert isinstance(args[0], Panel)
        assert "Model Error" in args[0].title
