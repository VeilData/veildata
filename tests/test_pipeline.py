from unittest.mock import MagicMock

from veildata.detectors import EntitySpan
from veildata.pipeline import DetectionPipeline
from veildata.revealers import TokenStore


def test_pipeline_masking():
    # Mock detector
    detector = MagicMock()
    detector.detect.return_value = [EntitySpan(7, 11, "PERSON", 1.0, "mock", "John")]

    pipeline = DetectionPipeline(detector)
    text = "Hello, John!"
    masked = pipeline(text)

    assert masked == "Hello, [REDACTED_1]!"
    assert pipeline.counter == 1


def test_pipeline_with_store():
    detector = MagicMock()
    detector.detect.return_value = [EntitySpan(7, 11, "PERSON", 1.0, "mock", "John")]

    store = TokenStore()
    pipeline = DetectionPipeline(detector, store=store)
    text = "Hello, John!"
    masked = pipeline(text)

    assert masked == "Hello, [REDACTED_1]!"
    assert store.mappings["[REDACTED_1]"] == "John"


def test_pipeline_multiple_spans():
    detector = MagicMock()
    detector.detect.return_value = [
        EntitySpan(0, 4, "A", 1.0, "mock", "1234"),
        EntitySpan(6, 10, "B", 1.0, "mock", "5678"),
    ]

    pipeline = DetectionPipeline(detector)
    text = "1234, 5678"
    masked = pipeline(text)

    assert masked == "[REDACTED_1], [REDACTED_2]"


def test_pipeline_overlapping_spans_filtered():
    # Pipeline should filter overlaps if detector returns them
    detector = MagicMock()
    detector.detect.return_value = [
        EntitySpan(0, 5, "A", 1.0, "mock", "12345"),
        EntitySpan(2, 6, "B", 1.0, "mock", "3456"),  # Overlaps
    ]

    pipeline = DetectionPipeline(detector)
    text = "123456"
    masked = pipeline(text)

    # Should keep first one (greedy)
    assert masked == "[REDACTED_1]6"


def test_pipeline_explain():
    detector = MagicMock()
    detector.detect.return_value = [
        EntitySpan(0, 4, "TEST", 0.9, "mock_detector", "test")
    ]

    pipeline = DetectionPipeline(detector)
    text = "test string"
    explanation = pipeline.explain(text)

    assert explanation["original"] == text
    assert len(explanation["detections"]) == 1
    det = explanation["detections"][0]
    assert det["start"] == 0
    assert det["end"] == 4
    assert det["text"] == "test"
    assert det["label"] == "TEST"
    assert det["detector"] == "mock_detector"
    assert det["score"] == 0.9


def test_pipeline_explain_overlapping():
    detector = MagicMock()
    detector.detect.return_value = [
        EntitySpan(0, 5, "A", 1.0, "mock", "12345"),
        EntitySpan(2, 6, "B", 1.0, "mock", "3456"),
    ]

    pipeline = DetectionPipeline(detector)
    text = "123456"
    explanation = pipeline.explain(text)

    # Should filter overlaps same as forward()
    assert len(explanation["detections"]) == 1
    assert explanation["detections"][0]["text"] == "12345"
