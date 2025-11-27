from unittest.mock import MagicMock, patch

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


@patch("veildata.detectors.spacy")
def test_spacy_detector(mock_spacy):
    # Mock spaCy model and doc
    mock_nlp = MagicMock()
    mock_spacy.load.return_value = mock_nlp
    mock_spacy.util.is_package.return_value = True

    mock_ent = MagicMock()
    mock_ent.label_ = "PERSON"
    mock_ent.start_char = 0
    mock_ent.end_char = 4
    mock_ent.text = "John"

    detector = SpacyDetector(pii_labels=["PERSON"])
    spans = detector.detect("John")

    assert len(spans) == 1
    assert spans[0].label == "PERSON"
    assert spans[0].text == "John"


@patch("veildata.detectors.pipeline")
def test_bert_detector(mock_pipeline):
    # Mock transformers pipeline
    mock_nlp = MagicMock()
    mock_pipeline.return_value = mock_nlp

    # Mock output
    mock_nlp.return_value = [
        {"entity_group": "PER", "score": 0.9, "start": 0, "end": 4, "word": "John"}
    ]

    detector = BertDetector()
    spans = detector.detect("John")

    assert len(spans) == 1
    assert spans[0].label == "PERSON"  # Mapped from PER
    assert spans[0].text == "John"


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
