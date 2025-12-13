from typer.testing import CliRunner

from veildata.cli import app

runner = CliRunner()


def test_cli_json_redaction(tmp_path):
    """Test JSON redaction via CLI."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    json_input = '{"key": "this is a test", "items": ["test 1", "test 2"]}'
    input_file = tmp_path / "input.json"
    input_file.write_text(json_input)

    result = runner.invoke(
        app,
        ["redact", str(input_file), "--json", "--config", str(config_file)],
    )
    assert result.exit_code == 0
    assert '"key": "this is a [TEST_1]"' in result.stdout
    assert '"items":' in result.stdout
    assert '"[TEST_2] 1"' in result.stdout


def test_cli_json_invalid(tmp_path):
    """Test invalid JSON input via CLI."""
    result = runner.invoke(
        app,
        ["redact", "not json", "--json"],
    )
    assert result.exit_code == 1
    assert "JSON Error" in result.stdout
