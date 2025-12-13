import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from veildata.cli import app
from veildata.exceptions import ConfigMissingError

runner = CliRunner()


def run_cli(args):
    """Helper to run the CLI via subprocess."""
    cmd = [sys.executable, "-m", "veildata.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def test_phone_regex_redaction(tmp_path):
    """Test basic phone number redaction via CLI."""
    # Create a simple config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'patterns:\n  PHONE: "\\\\b\\\\d{3}-\\\\d{3}-\\\\d{4}\\\\b"\n'
    )

    input_text = "Call me at 555-123-4567 today."
    result = run_cli(
        ["redact", input_text, "--method", "regex", "--config", str(config_file)]
    )

    assert result.returncode == 0, f"STDERR: {result.stderr}"
    assert "[PHONE_1]" in result.stdout
    assert "555-123-4567" not in result.stdout


def test_email_regex_redaction(tmp_path):
    """Test basic email redaction via CLI."""
    # Create a simple config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'patterns:\n  EMAIL: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}"\n'
    )

    input_text = "Email test@example.com for info."
    result = run_cli(
        ["redact", input_text, "--method", "regex", "--config", str(config_file)]
    )

    assert result.returncode == 0, f"STDERR: {result.stderr}"
    assert "[EMAIL_1]" in result.stdout
    assert "test@example.com" not in result.stdout


def test_cli_missing_config():
    """Test that CLI handles missing config file gracefully."""
    result = run_cli(["redact", "input.txt", "--config", "nonexistent_config.yaml"])
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
    result = run_cli(["redact", input_text, "--config", str(config_file)])

    # Should fail with model error, not ValueError about unknown method
    assert "ValueError" not in result.stderr
    assert "Unknown redaction method" not in result.stderr


def test_wizard_hybrid_config(tmp_path):
    """Test that wizard-generated hybrid config works."""
    # Create config like wizard would
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'method = "hybrid"\n\n[ml.spacy]\nenabled = true\nmodel = "en_core_web_lg"\n'
    )

    input_text = "Test email@example.com"
    # This will fail due to missing spacy model, but should not raise ValueError
    result = run_cli(["redact", input_text, "--config", str(config_file)])

    # Should fail with model error, not ValueError about unknown method
    assert "ValueError" not in result.stderr
    assert "Unknown redaction method" not in result.stderr


def test_cli_inspect():
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 0
    assert "Available Redaction Engines" in result.stdout
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


def test_cli_redact_preview(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    result = runner.invoke(
        app,
        [
            "redact",
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
    assert "[TEST_1]" in result.stdout


def test_cli_redact_explain(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    result = runner.invoke(
        app, ["redact", "this is a test", "--explain", "--config", str(config_file)]
    )
    assert result.exit_code == 0
    assert '"detections":' in result.stdout
    assert '"label": "TEST"' in result.stdout


def test_cli_reveal(tmp_path):
    # First redact and save store
    store_path = tmp_path / "tokens.json"
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    redact_result = runner.invoke(
        app,
        [
            "redact",
            "this is a test",
            "--store",
            str(store_path),
            "--config",
            str(config_file),
        ],
    )
    assert redact_result.exit_code == 0

    # Then reveal
    redacted_text = "this is a [TEST_1]"
    reveal_result = runner.invoke(
        app, ["reveal", redacted_text, "--store", str(store_path)]
    )
    assert reveal_result.exit_code == 0
    assert "this is a test" in reveal_result.stdout.strip()


def test_cli_benchmark(tmp_path):
    """Test that benchmark command runs and produces JSON output."""
    result = runner.invoke(
        app, ["benchmark", "--method", "regex", "--iterations", "5", "--size", "small"]
    )
    assert result.exit_code == 0
    assert "Benchmark Results" in result.stdout
    assert "regex" in result.stdout

    # Verify JSON was created
    import json

    bench_file = Path(".bench/last_run.json")
    assert bench_file.exists(), "Benchmark JSON file was not created"

    data = json.loads(bench_file.read_text())
    assert data["method"] == "regex"
    assert data["iterations"] == 5
    assert "avg_latency_ms" in data
    assert "p95_latency_ms" in data


def test_cli_redact_with_time(tmp_path):
    """Test that redact command with --time flag shows timing information."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    result = runner.invoke(
        app, ["redact", "this is a test", "--time", "--config", str(config_file)]
    )
    assert result.exit_code == 0
    assert "⏱️" in result.stdout
    assert "Load:" in result.stdout
    assert "Processing:" in result.stdout
    assert "Total:" in result.stdout
    assert "ms" in result.stdout


def test_cli_redact_with_time_and_output(tmp_path):
    """Test that redact command with --time flag works with file output."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')
    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app,
        [
            "redact",
            "this is a test",
            "--time",
            "--config",
            str(config_file),
            "--output",
            str(output_file),
        ],
    )
    assert result.exit_code == 0
    assert "⏱️" in result.stdout
    assert output_file.exists()


def test_cli_redact_with_time_dry_run(tmp_path):
    """Test that redact command with --time flag works in dry-run mode."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    result = runner.invoke(
        app,
        [
            "redact",
            "this is a test",
            "--time",
            "--dry-run",
            "--config",
            str(config_file),
        ],
    )
    assert result.exit_code == 0
    assert "⏱️" in result.stdout
    assert "Load:" in result.stdout
    assert "Processing:" in result.stdout


def test_cli_reveal_with_time(tmp_path):
    """Test that reveal command with --time flag shows timing information."""
    # First redact and save store
    store_path = tmp_path / "tokens.json"
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    redact_result = runner.invoke(
        app,
        [
            "redact",
            "this is a test",
            "--store",
            str(store_path),
            "--config",
            str(config_file),
        ],
    )
    assert redact_result.exit_code == 0

    # Then reveal with timing
    redacted_text = "this is a [TEST_1]"
    reveal_result = runner.invoke(
        app, ["reveal", redacted_text, "--store", str(store_path), "--time"]
    )
    assert reveal_result.exit_code == 0
    assert "this is a test" in reveal_result.stdout
    assert "⏱️" in reveal_result.stdout
    assert "Load:" in reveal_result.stdout
    assert "Processing:" in reveal_result.stdout
    assert "Total:" in reveal_result.stdout


# ============================================================================
# Merged In-Process Coverage Tests
# ============================================================================


def test_basic_redaction_in_process(tmp_path):
    """Test basic redaction in-process for coverage."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')
    result = runner.invoke(
        app, ["redact", "this is a test", "--config", str(config_file)]
    )
    assert result.exit_code == 0
    assert "[TEST_1]" in result.stdout


def test_stream_basic_in_process(tmp_path):
    """Test streaming mode in-process."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')
    input_file = tmp_path / "input.txt"
    input_file.write_text("test test test")
    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app,
        [
            "redact",
            str(input_file),
            "--stream",
            "--output",
            str(output_file),
            "--config",
            str(config_file),
        ],
    )
    assert result.exit_code == 0
    assert output_file.exists()


def test_redact_errors_in_process(tmp_path):
    """Test redaction errors in-process."""
    # Missing config handled by load_config exception
    result = runner.invoke(app, ["redact", "test", "--config", "missing.yaml"])
    assert result.exit_code == 1

    # Existing file no overwrite
    out = tmp_path / "exists.txt"
    out.write_text("exists")
    config = tmp_path / "conf.yaml"
    config.write_text('patterns:\n  A: "a"')
    result = runner.invoke(
        app, ["redact", "a", "--output", str(out), "--config", str(config)]
    )
    assert result.exit_code == 1


def test_redact_file_verbose_in_process(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')
    output_file = tmp_path / "output.txt"

    result = runner.invoke(
        app,
        [
            "redact",
            "test data",
            "--output",
            str(output_file),
            "--config",
            str(config_file),
            "--verbose",
        ],
    )
    assert result.exit_code == 0
    assert output_file.exists()
    assert "written to" in result.stdout or "✅" in result.stdout


def test_hybrid_defaults(tmp_path):
    """Test hybrid mode falls back to default patterns if none provided."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'method: "hybrid"\nml:\n  spacy:\n    enabled: true\n    model: "en_core_web_sm"\n'
    )
    with patch("veildata.engine.build_redactor") as mock_build:
        mock_build.return_value = (MagicMock(), MagicMock())
        result = runner.invoke(app, ["redact", "test", "--config", str(config_file)])
        assert result.exit_code == 0
        args, kwargs = mock_build.call_args
        config_arg = kwargs.get("config")
        assert config_arg is not None
        assert config_arg.patterns is not None


def test_regex_defaults_config(tmp_path):
    """Test regex mode defaults if no patterns."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('method: "regex"')

    with patch("veildata.engine.build_redactor") as mock_build:
        mock_build.return_value = (MagicMock(), MagicMock())
        result = runner.invoke(app, ["redact", "test", "--config", str(config_file)])
        assert result.exit_code == 0
        args, kwargs = mock_build.call_args
        config_arg = kwargs.get("config")
        assert config_arg is not None
        assert config_arg.patterns is not None


@patch("veildata.engine.build_redactor")
def test_build_redactor_error_handling(mock_build):
    """Test catching ConfigMissingError during build."""
    mock_build.side_effect = ConfigMissingError("Config error")
    result = runner.invoke(app, ["redact", "test"])
    assert result.exit_code == 1
    assert "Configuration Error" in result.stdout


@patch("veildata.engine.build_redactor")
def test_build_redactor_os_error(mock_build):
    """Test catching OSError (model download failure)."""
    mock_build.side_effect = OSError("Download failed")
    result = runner.invoke(app, ["redact", "test"])
    assert result.exit_code == 1
    assert "Model Error" in result.stdout
