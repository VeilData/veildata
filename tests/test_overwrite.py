from pathlib import Path

from typer.testing import CliRunner

from veildata.cli import app

runner = CliRunner()


def test_overwrite_protection():
    with runner.isolated_filesystem():
        # Create config file
        Path("config.yaml").write_text('patterns:\n  TEST: "test"')

        # Create existing output file
        Path("existing_output.txt").write_text("existing content")
        Path("existing_store.json").write_text("{}")

        # Test 1: Fail on existing output
        result = runner.invoke(
            app,
            [
                "mask",
                "test input",
                "-o",
                "existing_output.txt",
                "--config",
                "config.yaml",
            ],
        )
        assert result.exit_code == 1
        assert "Output file 'existing_output.txt' already exists" in result.stdout

        # Test 2: Fail on existing store
        result = runner.invoke(
            app,
            [
                "mask",
                "test input",
                "--store",
                "existing_store.json",
                "--config",
                "config.yaml",
            ],
        )
        assert result.exit_code == 1
        assert "TokenStore file 'existing_store.json' already exists" in result.stdout

        # Test 3: Success with --force on output
        result = runner.invoke(
            app,
            [
                "mask",
                "test input",
                "-o",
                "existing_output.txt",
                "--force",
                "--config",
                "config.yaml",
            ],
        )
        assert result.exit_code == 0
        assert Path("existing_output.txt").read_text() != "existing content"

        # Test 4: Success with --force on store
        result = runner.invoke(
            app,
            [
                "mask",
                "test input",
                "--store",
                "existing_store.json",
                "--force",
                "--config",
                "config.yaml",
            ],
        )
        assert result.exit_code == 0

        # Test 5: Dry run should not trigger store check
        result = runner.invoke(
            app,
            [
                "mask",
                "test input",
                "--store",
                "existing_store.json",
                "--dry-run",
                "--config",
                "config.yaml",
            ],
        )
        assert result.exit_code == 0
