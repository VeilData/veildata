from unittest.mock import MagicMock, patch

from veildata.detectors import (
    HybridDetector,
    RegexDetector,
    SpacyDetector,
)
from veildata.pipeline import DetectionPipeline
from veildata.revealers import TokenStore


def test_detection_pipeline_with_regex():
    """Test detection pipeline with regex detector."""
    patterns = {"EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
    detector = RegexDetector(patterns)
    store = TokenStore()
    pipeline = DetectionPipeline(detector, store=store)

    text = "Contact test@example.com"
    redacted = pipeline(text)
    assert "[REDACTED_1]" in redacted
    assert "test@example.com" not in redacted
    assert store.mappings["[REDACTED_1]"] == "test@example.com"


@patch("spacy.util.is_package", return_value=True)
@patch("rich.console.Console")
@patch("spacy.load")
def test_detection_pipeline_with_spacy(
    mock_spacy_load, mock_console_class, mock_is_package
):
    """Test detection pipeline with spaCy detector."""

    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    # Simulate the user responding 'y' (yes) to the model download prompt
    mock_console.input.return_value = "y"

    mock_nlp = MagicMock()
    mock_spacy_load.return_value = mock_nlp

    # Mock the doc object (the return value of calling the NLP object)
    mock_doc = MagicMock()

    # Mock the entity (the content of doc.ents)
    mock_ent = MagicMock()
    mock_ent.label_ = "PERSON"
    mock_ent.start_char = 0
    mock_ent.end_char = 4
    mock_ent.text = "John"

    mock_doc.ents = [mock_ent]

    # Set the mocked doc as the return value of the mocked NLP object
    # The detector calls nlp(text)
    mock_nlp.return_value = mock_doc

    # Initialize the detector and pipeline
    # The SpacyDetector init calls spacy.load(), which returns mock_nlp
    detector = SpacyDetector(pii_labels=["PERSON"])
    pipeline = DetectionPipeline(detector)

    text = "John works at Apple"
    result = pipeline(text)

    assert "[REDACTED_1]" in result
    assert "Apple" in result
    assert "John" not in result

    # Verify spacy.load was called during initialization
    mock_spacy_load.assert_called()


@patch("spacy.util.is_package", return_value=True)
@patch("rich.console.Console")
def test_hybrid_detection_pipeline(mock_console_class, mock_is_package):
    """Test hybrid detection pipeline with multiple detectors."""

    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "y"

    # Create mock detectors
    patterns = {"EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
    regex_detector = RegexDetector(patterns)

    # Mock spaCy detector
    mock_nlp = MagicMock()
    with patch("spacy.load", return_value=mock_nlp):
        mock_doc = MagicMock()
        mock_ent = MagicMock()
        mock_ent.label_ = "PERSON"
        mock_ent.start_char = 0
        mock_ent.end_char = 4
        mock_ent.text = "John"
        mock_doc.ents = [mock_ent]
        mock_nlp.return_value = mock_doc

        spacy_detector = SpacyDetector(pii_labels=["PERSON"])

        # Create hybrid detector
        hybrid_detector = HybridDetector(
            [regex_detector, spacy_detector], strategy="union", prefer="ml"
        )

        # Create pipeline
        store = TokenStore()
        pipeline = DetectionPipeline(hybrid_detector, store=store)

        # Test with text containing both email and person
        text = "John's email is john@example.com"
        redacted = pipeline(text)

        # Both should be redacted
        assert "[REDACTED_1]" in redacted  # John
        assert "[REDACTED_2]" in redacted  # email
        assert "john@example.com" not in redacted

        # Verify store
        assert len(store.mappings) == 2
        assert "John" in store.mappings.values()
        assert "john@example.com" in store.mappings.values()


def test_pipeline_with_custom_redaction_format():
    """Test pipeline with custom redaction format."""
    patterns = {"EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
    detector = RegexDetector(patterns)
    store = TokenStore()

    # Custom redaction format
    pipeline = DetectionPipeline(
        detector, store=store, redaction_format="[MASKED_{counter}]"
    )

    text = "Contact test@example.com"
    redacted = pipeline(text)

    assert "[MASKED_1]" in redacted
    assert store.mappings["[MASKED_1]"] == "test@example.com"
    assert store.reveal(redacted) == text
