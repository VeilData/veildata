from pathlib import Path

from typer.testing import CliRunner

from veildata.cli import app

runner = CliRunner()


def test_e2e_mask_unmask_flow():
    """
    Verify the full lifecycle:
    1. Create input file
    2. Mask it (output to file, save store)
    3. Unmask it (read from file, use store)
    4. Verify original content is restored
    """
    with runner.isolated_filesystem():
        # Setup
        input_text = "My email is test@example.com and my phone is 555-0199."
        Path("input.txt").write_text(input_text)

        # Config for regex
        # Note: Using double backslashes for regex in yaml string
        config_content = 'patterns:\n  EMAIL: "\\\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\\\.[A-Z|a-z]{2,}\\\\b"'
        Path("config.yaml").write_text(config_content)

        # Step 1: Mask
        # veildata mask input.txt -o masked.txt --store store.json --config config.yaml
        result = runner.invoke(
            app,
            [
                "mask",
                "input.txt",
                "-o",
                "masked.txt",
                "--store",
                "store.json",
                "--config",
                "config.yaml",
            ],
        )
        assert result.exit_code == 0

        # Verify masked output
        masked_content = Path("masked.txt").read_text()
        assert "[REDACTED_" in masked_content
        assert "test@example.com" not in masked_content
        assert Path("store.json").exists()

        # Debug: Print store content
        store_content = Path("store.json").read_text()
        assert "{}" not in store_content, "Store is empty!"

        # Step 2: Unmask
        # veildata unmask masked.txt --store store.json
        result = runner.invoke(app, ["unmask", "masked.txt", "--store", "store.json"])
        assert result.exit_code == 0

        # Verify output matches original (ignoring potential newline differences from print)
        assert input_text in result.stdout
