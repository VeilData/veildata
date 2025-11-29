import subprocess
import sys


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
