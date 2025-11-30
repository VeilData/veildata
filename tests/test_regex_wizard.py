import subprocess
import sys


def run_cli(args):
    """Helper to run the CLI via subprocess."""
    cmd = [sys.executable, "-m", "veildata.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def test_wizard_regex_config(tmp_path):
    """Test that wizard-generated regex config works (uses default patterns)."""
    # Create config like wizard would (just method="regex", no patterns)
    config_file = tmp_path / "config.toml"
    config_file.write_text('method = "regex"\n')

    input_text = "Call 555-123-4567"
    result = run_cli(["mask", input_text, "--config", str(config_file)])

    assert result.returncode == 0, f"STDERR: {result.stderr}"
    assert "[REDACTED_1]" in result.stdout
    assert "555-123-4567" not in result.stdout
