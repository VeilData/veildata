from pathlib import Path

from typer.testing import CliRunner

from veildata.cli import app

runner = CliRunner()


def test_oneshot_mask_unmask():
    with runner.isolated_filesystem():
        # Test Masking
        result = runner.invoke(app, ["mask", "My email is test@example.com"])
        assert result.exit_code == 0
        assert "[REDACTED_" in result.stdout
        masked_output = result.stdout.strip()

        # Verify token store exists
        assert Path("token_store.json").exists()

        # Test Unmasking
        result_unmask = runner.invoke(app, ["unmask", masked_output])
        assert result_unmask.exit_code == 0
        assert "test@example.com" in result_unmask.stdout
