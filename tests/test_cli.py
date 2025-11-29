import subprocess
import sys
from pathlib import Path


def test_phone_regex_masking(tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("Email: john@example.com, Phone: 555-123-4567")
    store_file = tmp_path / "mappings.json"
    config_file = Path(__file__).parent / "data" / "test_regex_phone_mask_config.yaml"
    output_file = tmp_path / "masked.txt"

    result = subprocess.run(
        [
            "uv",
            "run",
            "veildata",
            "mask",
            str(input_file),
            "-m",
            "regex",
            "--store",
            str(store_file),
            "-o",
            str(output_file),
            "--config",
            str(config_file),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    masked = output_file.read_text()
    assert "[REDACTED_" in masked
    assert "john@example.com" in masked
    assert "555-123-4567" not in masked


def test_email_regex_masking(tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("Email: john@example.com, Phone: 555-123-4567")
    store_file = tmp_path / "mappings.json"
    config_file = Path(__file__).parent / "data" / "test_regex_email_mask_config.yaml"
    output_file = tmp_path / "masked.txt"

    result = subprocess.run(
        [
            "uv",
            "run",
            "veildata",
            "mask",
            str(input_file),
            "-m",
            "regex",
            "--store",
            str(store_file),
            "-o",
            str(output_file),
            "--config",
            str(config_file),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    masked = output_file.read_text()
    assert "john@example.com" not in masked
    assert "555-123-4567" in masked


def test_cli_missing_config(tmp_path):
    """Test that CLI shows friendly error message when config file is missing."""
    input_file = tmp_path / "input.txt"
    input_file.write_text("Some text")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "veildata.cli",
            "mask",
            str(input_file),
            "--config",
            "non_existent_config.yaml",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Configuration file not found" in result.stdout
    assert "non_existent_config.yaml" in result.stdout
