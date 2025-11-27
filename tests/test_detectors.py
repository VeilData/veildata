from unittest.mock import MagicMock

from veildata.detectors import (
    EntitySpan,
    HybridDetector,
    RegexDetector,
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
