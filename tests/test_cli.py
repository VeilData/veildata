import subprocess
import sys
from unittest.mock import patch

from typer.testing import CliRunner

from veildata.cli import app

runner = CliRunner()


def run_cli(args):
    """Helper to run the CLI via subprocess."""
    cmd = [sys.executable, "-m", "veildata.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def test_phone_regex_masking(tmp_path):
    """Test basic phone number masking via CLI."""
    # Create a simple config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'patterns:\n  PHONE: "\\\\b\\\\d{3}-\\\\d{3}-\\\\d{4}\\\\b"\n'
    )

    input_text = "Call me at 555-123-4567 today."
    result = run_cli(
        ["mask", input_text, "--method", "regex", "--config", str(config_file)]
    )

    assert result.returncode == 0, f"STDERR: {result.stderr}"
    assert "[REDACTED_1]" in result.stdout
    assert "555-123-4567" not in result.stdout


def test_email_regex_masking(tmp_path):
    """Test basic email masking via CLI."""
    # Create a simple config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'patterns:\n  EMAIL: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}"\n'
    )

    input_text = "Email test@example.com for info."
    result = run_cli(
        ["mask", input_text, "--method", "regex", "--config", str(config_file)]
    )

    assert result.returncode == 0, f"STDERR: {result.stderr}"
    assert "[REDACTED_1]" in result.stdout
    assert "test@example.com" not in result.stdout


def test_cli_missing_config():
    """Test that CLI handles missing config file gracefully."""
    result = run_cli(["mask", "input.txt", "--config", "nonexistent_config.yaml"])
    assert result.returncode == 1
    assert "Configuration Error" in result.stdout


def test_wizard_spacy_config(tmp_path):
    """Test that wizard-generated spacy config works."""
    # Create config like wizard would
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'method = "spacy"\n\n[ml.spacy]\nenabled = true\nmodel = "en_core_web_lg"\n'
    )

    input_text = "Test text"
    # This will fail due to missing model, but should not raise ValueError
    result = run_cli(["mask", input_text, "--config", str(config_file)])

    # Should fail with model error, not ValueError about unknown method
    assert "ValueError" not in result.stderr
    assert "Unknown masking method" not in result.stderr


def test_wizard_hybrid_config(tmp_path):
    """Test that wizard-generated hybrid config works."""
    # Create config like wizard would
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'method = "hybrid"\n\n[ml.spacy]\nenabled = true\nmodel = "en_core_web_lg"\n'
    )

    input_text = "Test email@example.com"
    # This will fail due to missing spacy model, but should not raise ValueError
    result = run_cli(["mask", input_text, "--config", str(config_file)])

    # Should fail with model error, not ValueError about unknown method
    assert "ValueError" not in result.stderr
    assert "Unknown masking method" not in result.stderr


def test_cli_inspect():
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 0
    assert "Available Masking Engines" in result.stdout
    assert "regex" in result.stdout
    assert "spacy" in result.stdout


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "VeilData" in result.stdout


@patch("veildata.cli.check_python")
@patch("veildata.cli.check_os")
@patch("veildata.cli.check_spacy")
@patch("veildata.cli.check_version")
@patch("veildata.cli.check_engines")
@patch("veildata.cli.check_write_permissions")
@patch("veildata.cli.check_docker")
@patch("veildata.cli.check_ghcr")
def test_cli_doctor(
    mock_ghcr,
    mock_docker,
    mock_write,
    mock_engines,
    mock_version,
    mock_spacy,
    mock_os,
    mock_python,
):
    # Setup mocks to return success
    mock_python.return_value = ("Python", "3.10", "OK")
    mock_os.return_value = ("OS", "Linux", "OK")
    mock_spacy.return_value = ("Spacy", "Installed", "OK")
    mock_version.return_value = ("Version", "0.1.0", "OK")
    mock_engines.return_value = ("Engines", "All Good", "OK")
    mock_write.return_value = ("Write", "Writable", "OK")
    mock_docker.return_value = ("Docker", "Running", "OK")
    mock_ghcr.return_value = ("GHCR", "Accessible", "OK")

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "All checks passed!" in result.stdout


@patch("veildata.wizard.run_wizard")
def test_cli_init(mock_wizard):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    mock_wizard.assert_called_once()


def test_cli_mask_preview(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    result = runner.invoke(
        app,
        [
            "mask",
            "this is a test",
            "--preview",
            "1",
            "--dry-run",
            "--config",
            str(config_file),
        ],
    )
    assert result.exit_code == 0
    assert "Preview" in result.stdout
    assert "[REDACTED_1]" in result.stdout


def test_cli_mask_explain(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    result = runner.invoke(
        app, ["mask", "this is a test", "--explain", "--config", str(config_file)]
    )
    assert result.exit_code == 0
    assert '"detections":' in result.stdout
    assert '"label": "TEST"' in result.stdout


def test_cli_unmask(tmp_path):
    # First mask and save store
    store_path = tmp_path / "tokens.json"
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    mask_result = runner.invoke(
        app,
        [
            "mask",
            "this is a test",
            "--store",
            str(store_path),
            "--config",
            str(config_file),
        ],
    )
    assert mask_result.exit_code == 0

    # Then unmask
    masked_text = "this is a [REDACTED_1]"
    unmask_result = runner.invoke(
        app, ["unmask", masked_text, "--store", str(store_path)]
    )
    assert unmask_result.exit_code == 0
    assert "this is a test" in unmask_result.stdout.strip()
