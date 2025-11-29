import os
from unittest.mock import MagicMock, patch

import pytest

from veildata.detectors import (
    BertDetector,
    EntitySpan,
    HybridDetector,
    RegexDetector,
    SpacyDetector,
)


def test_regex_detector():
    patterns = {"EMAIL": r"[a-z]+@[a-z]+\.com"}
    detector = RegexDetector(patterns)
    text = "Contact test@example.com"
    spans = detector.detect(text)

    assert len(spans) == 1
    assert spans[0].label == "EMAIL"
    assert spans[0].text == "test@example.com"
    assert spans[0].start == 8
    assert spans[0].end == 24


def test_hybrid_detector_union():
    # Mock detectors
    d1 = MagicMock()
    d1.detect.return_value = [EntitySpan(0, 4, "PERSON", 0.9, "spacy", "John")]

    d2 = MagicMock()
    d2.detect.return_value = [EntitySpan(10, 15, "EMAIL", 1.0, "regex", "a@b.c")]

    hybrid = HybridDetector([d1, d2])
    spans = hybrid.detect("John ... a@b.c")

    assert len(spans) == 2
    assert spans[0].text == "John"
    assert spans[1].text == "a@b.c"


def test_hybrid_detector_overlap_resolution():
    # Overlapping spans
    span1 = EntitySpan(0, 10, "PERSON", 0.8, "spacy", "John Smith")
    span2 = EntitySpan(5, 10, "NAME", 0.9, "regex", "Smith")

    d1 = MagicMock()
    d1.detect.return_value = [span1]
    d2 = MagicMock()
    d2.detect.return_value = [span2]

    # Prefer ML (default)
    hybrid = HybridDetector([d1, d2], prefer="ml")
    spans = hybrid.detect("John Smith")
    assert len(spans) == 1
    assert spans[0] == span1  # spacy wins

    # Prefer Rules
    hybrid_rules = HybridDetector([d1, d2], prefer="rules")
    spans_rules = hybrid_rules.detect("John Smith")
    assert len(spans_rules) == 1
    assert spans_rules[0] == span2  # regex wins (assuming source check works)


@patch("rich.console.Console")
@patch("spacy.util.is_package")
@patch("spacy.load")
@patch("subprocess.run")
def test_spacy_detector_download_accepted(
    mock_run, mock_load, mock_is_package, mock_console_class
):
    """Test SpacyDetector when user accepts download prompt."""
    # Mock console instance
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "y"

    # Model not installed
    mock_is_package.return_value = False

    # Mock successful subprocess download
    mock_run.return_value = MagicMock(returncode=0)

    # Mock spacy.load to succeed after download
    mock_nlp = MagicMock()
    mock_load.return_value = mock_nlp

    _ = SpacyDetector(model="en_core_web_sm")

    # Verify download was prompted
    mock_console.input.assert_called_once()
    assert "Download" in mock_console.input.call_args[0][0]

    # Verify subprocess was called to download
    mock_run.assert_called_once()
    assert "spacy" in str(mock_run.call_args)
    assert "download" in str(mock_run.call_args)


@patch("rich.console.Console")
@patch("spacy.util.is_package")
def test_spacy_detector_download_declined(mock_is_package, mock_console_class):
    """Test SpacyDetector when user declines download prompt."""
    # Mock console instance
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "n"

    # Model not installed
    mock_is_package.return_value = False

    # Should raise OSError when user declines
    with pytest.raises(OSError) as exc_info:
        SpacyDetector(model="en_core_web_sm")

    assert "download declined" in str(exc_info.value)


@patch("rich.console.Console")
@patch("os.getenv")
def test_bert_detector_download_accepted(mock_getenv, mock_console_class):
    """Test BertDetector when user accepts download prompt."""
    import sys

    # Mock console instance
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "y"

    # Smart mock for os.getenv
    def getenv_side_effect(key, default=None):
        if key == "TRANSFORMERS_CACHE":
            return "/tmp/nonexistent_cache_dir_for_testing"
        return os.environ.get(key, default)

    mock_getenv.side_effect = getenv_side_effect

    # Mock transformers module
    mock_transformers = MagicMock()
    # Ensure pipeline is a mock
    mock_pipeline = MagicMock()
    mock_transformers.pipeline = mock_pipeline

    with patch.dict(
        sys.modules,
        {
            "transformers": mock_transformers,
            "transformers.utils": mock_transformers.utils,
        },
    ):
        _ = BertDetector(model_name="dslim/bert-base-NER")

        # Verify user was prompted
        mock_console.input.assert_called_once()
        assert "Download" in mock_console.input.call_args[0][0]

        # Verify pipeline was initialized
        # Note: Since we mocked the module, the 'pipeline' imported in detectors.py is mock_transformers.pipeline
        mock_transformers.pipeline.assert_called_once()


@patch("rich.console.Console")
@patch("os.getenv")
def test_bert_detector_download_declined(mock_getenv, mock_console_class):
    """Test BertDetector when user declines download prompt."""
    import sys

    # Mock console instance
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "n"

    # Smart mock for os.getenv
    def getenv_side_effect(key, default=None):
        if key == "TRANSFORMERS_CACHE":
            return "/tmp/nonexistent_cache_dir_for_testing"
        return os.environ.get(key, default)

    mock_getenv.side_effect = getenv_side_effect

    # Mock transformers module
    mock_transformers = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "transformers": mock_transformers,
            "transformers.utils": mock_transformers.utils,
        },
    ):
        # Should raise OSError when user declines
        with pytest.raises(OSError) as exc_info:
            BertDetector(model_name="dslim/bert-base-NER")

        assert "download declined" in str(exc_info.value)
