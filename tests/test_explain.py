import json
import subprocess
import sys


def run_cli(args):
    """Helper to run the CLI via subprocess."""
    cmd = [sys.executable, "-m", "veildata.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def test_explain_mode_regex(tmp_path):
    """Test --explain with regex detection."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'patterns:\n  EMAIL: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}"\n'
    )

    input_text = "Contact me at test@example.com for details."
    result = run_cli(
        [
            "redact",
            input_text,
            "--method",
            "regex",
            "--config",
            str(config_file),
            "--explain",
        ]
    )

    assert result.returncode == 0, f"STDERR: {result.stderr}"

    # Parse JSON output
    explanation = json.loads(result.stdout)

    assert "original" in explanation
    assert "detections" in explanation
    assert explanation["original"] == input_text
    assert len(explanation["detections"]) == 1

    detection = explanation["detections"][0]
    assert detection["text"] == "test@example.com"
    assert detection["label"] == "EMAIL"
    assert detection["detector"] == "regex"
    assert detection["score"] == 1.0


def test_explain_mode_output_file(tmp_path):
    """Test --explain with output file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'patterns:\n  PHONE: "\\\\b\\\\d{3}-\\\\d{3}-\\\\d{4}\\\\b"\n'
    )

    output_file = tmp_path / "explanation.json"
    input_text = "Call 555-123-4567"

    result = run_cli(
        [
            "redact",
            input_text,
            "--method",
            "regex",
            "--config",
            str(config_file),
            "--explain",
            "--output",
            str(output_file),
        ]
    )

    assert result.returncode == 0
    assert output_file.exists()

    # Read and parse JSON
    with open(output_file) as f:
        explanation = json.load(f)

    assert len(explanation["detections"]) == 1
    assert explanation["detections"][0]["text"] == "555-123-4567"
    assert explanation["detections"][0]["detector"] == "regex"


def test_explain_mode_no_detections(tmp_path):
    """Test --explain when no PII is detected."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'patterns:\n  EMAIL: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}"\n'
    )

    input_text = "This text has no PII."
    result = run_cli(
        [
            "redact",
            input_text,
            "--method",
            "regex",
            "--config",
            str(config_file),
            "--explain",
        ]
    )

    assert result.returncode == 0
    explanation = json.loads(result.stdout)

    assert explanation["original"] == input_text
    assert len(explanation["detections"]) == 0
