from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from veildata.cli import app

runner = CliRunner()


def test_cli_pipe(tmp_path):
    """Test pipe command functionality."""
    # Create a config
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    # Mock stdin via input arg
    input_data = "this is a test line\nanother test line"

    result = runner.invoke(
        app, ["pipe", "--config", str(config_file)], input=input_data
    )

    assert result.exit_code == 0
    assert "[TEST_1]" in result.stdout


def test_cli_json_mode(tmp_path):
    """Test redaction with --json flag."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    input_json = '{"key": "this is a test", "nested": ["test item"]}'

    result = runner.invoke(
        app, ["redact", input_json, "--json", "--config", str(config_file)]
    )

    assert result.exit_code == 0
    assert "[TEST_1]" in result.stdout
    assert '"key":' in result.stdout  # Structure preserved


def test_cli_no_ml_flag(tmp_path):
    """Test --no-ml flag forces rules mode."""
    config_file = tmp_path / "config.yaml"
    # Use valid enum value ner_spacy
    config_file.write_text(
        'method: "ner_spacy"\nml:\n  spacy:\n    enabled: true\n    model: "en_core_web_sm"\n'
    )

    # Mock build_redactor to check arguments
    with patch("veildata.engine.build_redactor") as mock_build:
        mock_build.return_value = (MagicMock(), MagicMock())

        result = runner.invoke(
            app, ["redact", "test", "--no-ml", "--config", str(config_file)]
        )

        assert result.exit_code == 0
        args, kwargs = mock_build.call_args
        assert kwargs.get("detect_mode") == "rules"


def test_cli_method_override(tmp_path):
    """Test that config method overrides CLI default but not explicit CLI arg."""
    config_file = tmp_path / "config.yaml"
    # Use valid enum value ner_spacy
    config_file.write_text('method: "ner_spacy"\npatterns:\n  TEST: "test"\n')

    with patch("veildata.engine.build_redactor") as mock_build:
        mock_build.return_value = (MagicMock(), MagicMock())

        # 1. CLI default (regex) vs Config (ner_spacy) -> Should use ner_spacy
        runner.invoke(app, ["redact", "test", "--config", str(config_file)])
        args, _ = mock_build.call_args
        assert args[0] == "ner_spacy"

        # 2. Explicit CLI (bert) vs Config (ner_spacy) -> Should use ner_bert
        # Note: CLI arg 'bert' is mapped to 'ner_bert' inside the function
        runner.invoke(
            app, ["redact", "test", "--method", "bert", "--config", str(config_file)]
        )
        args, _ = mock_build.call_args
        assert args[0] == "ner_bert"


def test_cli_store_exists_error(tmp_path):
    """Test error when store file exists and no --force."""
    store_file = tmp_path / "store.json"
    store_file.touch()

    result = runner.invoke(app, ["redact", "test", "--store", str(store_file)])

    # Normalize whitespace to handle wrapping
    stdout_normalized = " ".join(result.stdout.split())
    assert "already exists" in stdout_normalized


def test_cli_explain_errors():
    """Test explain mode errors."""
    # Mock a redactor that doesn't support explain (e.g. valid but composition)
    mock_redactor = MagicMock()
    del mock_redactor.detector  # Not a detection pipeline
    del mock_redactor.modules

    with patch(
        "veildata.engine.build_redactor", return_value=(mock_redactor, MagicMock())
    ):
        result = runner.invoke(app, ["redact", "test", "--explain"])
        assert result.exit_code == 1
        assert "only supported in detector-based modes" in result.stdout


def test_cli_json_error(tmp_path):
    """Test invalid JSON input with --json."""
    result = runner.invoke(app, ["redact", "{invalid json", "--json"])
    assert result.exit_code == 1
    assert "JSON Error" in result.stdout


@patch("veildata.wizard.run_wizard")
@patch("rich.prompt.Confirm.ask", return_value=True)
def test_cli_wizard_prompt_yes(mock_confirm, mock_wizard):
    """Test wizard prompt appears and is accepted."""
    from veildata.cli import redact

    # Mock Path.home() to return a mock object chain
    with patch("pathlib.Path.home") as mock_home:
        # Setup the mock chain: Path.home() / ".veildata" / "config.toml"
        mock_root = mock_home.return_value
        mock_config = mock_root / ".veildata" / "config.toml"

        # Configure exists(): False (trigger), True (check), True (final)
        mock_config.exists.side_effect = [False, True, True]
        mock_config.__str__.return_value = "/mock/home/.veildata/config.toml"

        with patch("veildata.engine.build_redactor") as mock_build, patch(
            "veildata.engine.load_config"
        ) as mock_load, patch("sys.stdin") as mock_stdin:

            mock_stdin.isatty.return_value = True

            mock_build.return_value = (MagicMock(), MagicMock())
            mock_load.return_value = MagicMock(method=MagicMock(value="regex"))

            # Call redact directly to bypass CliRunner isolation for isatty
            # Must pass all arguments as defaults are Typer Option objects
            redact(
                input="test",
                output=None,
                config_path=None,
                method="regex",
                dry_run=False,
                verbose=False,
                store_path=None,
                preview=0,
                detect_mode="rules",
                ml_config=None,
                no_ml=False,
                force=False,
                explain=False,
                show_time=False,
                stream=False,
                chunk_size=4096,
                overlap=512,
                is_json=False,
            )

            mock_confirm.assert_called_once()
            mock_wizard.assert_called_once()


def test_cli_pipe_error(tmp_path):
    """Test pipe error handling."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('patterns:\n  TEST: "test"\n')

    # Mock redactor to raise exception
    mock_redactor = MagicMock(side_effect=Exception("Stream failure"))

    with patch(
        "veildata.engine.build_redactor", return_value=(mock_redactor, MagicMock())
    ):
        result = runner.invoke(
            app, ["pipe", "--config", str(config_file)], input="test line"
        )

        assert result.exit_code == 1
        assert "Stream failure" in result.stderr or "Stream failure" in result.stdout


@patch("veildata.wizard.run_wizard")
@patch("rich.prompt.Confirm.ask")
def test_cli_wizard_prompt_no(mock_confirm, mock_wizard):
    """Test wizard prompt appears but is declined."""
    mock_confirm.return_value = False

    from veildata.cli import redact

    # Mock Path.home()
    with patch("pathlib.Path.home") as mock_home:
        mock_root = mock_home.return_value
        mock_config = mock_root / ".veildata" / "config.toml"

        # Exists returns False to trigger prompt
        mock_config.exists.return_value = False

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True

            # If declined, it should continue (and maybe use defaults or fail later if config needed)
            # Based on cli.py code inspection, it just continues.
            redact(
                input="test",
                output=None,
                config_path=None,
                method="regex",
                dry_run=False,
                verbose=False,
                store_path=None,
                preview=0,
                detect_mode="rules",
                ml_config=None,
                no_ml=False,
                force=False,
                explain=False,
                show_time=False,
                stream=False,
                chunk_size=4096,
                overlap=512,
                is_json=False,
            )

            mock_confirm.assert_called_once()
            mock_wizard.assert_not_called()
