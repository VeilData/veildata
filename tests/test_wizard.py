from unittest.mock import patch

from veildata.wizard import run_wizard


@patch("veildata.wizard.console")
@patch("veildata.wizard.Prompt.ask")
@patch("veildata.wizard.Confirm.ask")
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.write_text")
def test_run_wizard_regex(
    mock_write, mock_mkdir, mock_confirm, mock_prompt, mock_console
):
    """Test wizard with regex engine selection."""
    # Setup mocks
    mock_prompt.side_effect = ["regex"]  # Choose regex
    mock_confirm.return_value = True  # Save config

    # Run wizard
    run_wizard()

    # Verify prompts
    assert mock_prompt.call_count == 1

    # Verify config writing
    mock_mkdir.assert_called_once()
    mock_write.assert_called_once()

    # Check content
    content = mock_write.call_args[0][0]
    assert 'method = "regex"' in content
    assert "[ml.spacy]" not in content


@patch("veildata.wizard.console")
@patch("veildata.wizard.Prompt.ask")
@patch("veildata.wizard.Confirm.ask")
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.write_text")
def test_run_wizard_spacy(
    mock_write, mock_mkdir, mock_confirm, mock_prompt, mock_console
):
    """Test wizard with spacy engine selection."""
    # Setup mocks
    mock_prompt.side_effect = ["spacy", "en_core_web_sm"]  # Choose spacy, then model
    mock_confirm.return_value = True

    # Run wizard
    run_wizard()

    # Verify prompts
    assert mock_prompt.call_count == 2

    # Verify config writing
    mock_write.assert_called_once()

    # Check content
    content = mock_write.call_args[0][0]
    assert 'method = "spacy"' in content
    assert "[ml.spacy]" in content
    assert 'model = "en_core_web_sm"' in content


@patch("veildata.wizard.console")
@patch("veildata.wizard.Prompt.ask")
@patch("veildata.wizard.Confirm.ask")
@patch("pathlib.Path.write_text")
def test_run_wizard_cancel(mock_write, mock_confirm, mock_prompt, mock_console):
    """Test wizard cancellation."""
    mock_prompt.return_value = "regex"
    mock_confirm.return_value = False  # Do not save

    run_wizard()

    mock_write.assert_not_called()
