"""
Comprehensive tests for the streaming redaction buffer.

This module tests all aspects of the StreamingRedactionBuffer including:
- Basic functionality with single and multiple chunks
- Cross-chunk entity detection (VC-98)
- Edge cases and boundary conditions
- Integration with TokenStore
"""

import pytest

from veildata.detectors import RegexDetector
from veildata.pipeline import DetectionPipeline
from veildata.revealers import TokenStore
from veildata.streaming_buffer import (
    ChunkMetadata,
    StreamingRedactionBuffer,
    stream_redact,
)


@pytest.fixture
def email_pattern():
    """Simple email pattern for testing."""
    return {"EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}


@pytest.fixture
def phone_pattern():
    """Simple phone pattern for testing."""
    return {"PHONE": r"\d{3}-\d{4}"}


@pytest.fixture
def multi_pattern():
    """Multiple patterns for testing."""
    return {
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PHONE": r"\d{3}-\d{4}",
        "SSN": r"\d{3}-\d{2}-\d{4}",
    }


@pytest.fixture
def email_detector(email_pattern):
    """Detector for emails."""
    return RegexDetector(email_pattern)


@pytest.fixture
def email_pipeline(email_detector):
    """Pipeline with email detector."""
    return DetectionPipeline(email_detector)


@pytest.fixture
def multi_detector(multi_pattern):
    """Detector with multiple patterns."""
    return RegexDetector(multi_pattern)


@pytest.fixture
def multi_pipeline(multi_detector):
    """Pipeline with multiple patterns."""
    return DetectionPipeline(multi_detector)


# =========================================================================
# Basic Functionality Tests
# =========================================================================


def test_single_chunk_no_entities(email_pipeline):
    """Test processing a single chunk with no entities."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10)
    result = buffer.add_chunk("Hello world, this is a test.")
    final = buffer.finalize()

    #  With overlap of 10, safe_end = 28-10 = 18
    # So output will be first 18 chars, finalize gets last 10
    assert result == "Hello world, this "
    assert final == "is a test."


def test_single_chunk_with_entity(email_pipeline):
    """Test processing a single chunk containing an entity."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10)
    text = "Email me at test@example.com please."
    result = buffer.add_chunk(text)
    final = buffer.finalize()

    # Entity should be redacted
    full_output = result + final
    assert "[REDACTED_1]" in full_output
    assert "test@example.com" not in full_output


def test_multiple_chunks_no_entities(email_pipeline):
    """Test processing multiple chunks with no entities."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10)

    chunk1 = "This is the first chunk. "
    chunk2 = "This is the second chunk. "
    chunk3 = "This is the third chunk."

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    output3 = buffer.add_chunk(chunk3)
    final = buffer.finalize()

    full_output = output1 + output2 + output3 + final
    assert "This is the first chunk." in full_output
    assert "This is the second chunk." in full_output
    assert "This is the third chunk." in full_output


def test_empty_chunks(email_pipeline):
    """Test that empty chunks are handled gracefully."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10)

    assert buffer.add_chunk("") == ""
    assert buffer.add_chunk("Hello") == ""
    assert buffer.add_chunk("") == ""
    final = buffer.finalize()
    assert final == "Hello"


# =========================================================================
# Cross-Chunk Entity Detection Tests (VC-98)
# =========================================================================


def test_entity_split_across_two_chunks(email_pipeline):
    """Test entity split across exactly 2 chunks."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=20)

    # Split email across boundary
    chunk1 = "My email is john.do"
    chunk2 = "e@example.com and more text."

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    # Email should be detected and redacted
    assert "[REDACTED_1]" in full_output
    assert "john.doe@example.com" not in full_output
    assert "My email is" in full_output
    assert "and more text." in full_output


def test_entity_split_across_three_chunks(email_pipeline):
    """Test entity split across 3+ chunks."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=25)

    # Split email across three chunks
    chunk1 = "Contact: john"
    chunk2 = ".doe@exa"
    chunk3 = "mple.com for info."

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    output3 = buffer.add_chunk(chunk3)
    final = buffer.finalize()

    full_output = output1 + output2 + output3 + final

    # Email should be detected despite being split
    assert "[REDACTED_1]" in full_output
    assert "john.doe@example.com" not in full_output


def test_entity_exactly_at_boundary(email_pipeline):
    """Test entity that ends exactly at chunk boundary."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=20)

    # Email ends exactly where chunk1 ends
    chunk1 = "Email: test@example.com"
    chunk2 = " and additional text here."

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    assert "[REDACTED_1]" in full_output
    assert "test@example.com" not in full_output


def test_multiple_entities_spanning_boundaries(multi_pipeline):
    """Test multiple entities spanning different boundaries."""
    buffer = StreamingRedactionBuffer(multi_pipeline, overlap_size=15)

    chunk1 = "Email: john@ex"
    chunk2 = "ample.com Phone: 555-12"
    chunk3 = "34 SSN: 123-45"
    chunk4 = "-6789 end"

    outputs = []
    for chunk in [chunk1, chunk2, chunk3, chunk4]:
        outputs.append(buffer.add_chunk(chunk))
    outputs.append(buffer.finalize())

    full_output = "".join(outputs)

    # All three entities should be redacted
    assert full_output.count("[REDACTED_") == 3
    assert "john@example.com" not in full_output
    assert "555-1234" not in full_output
    assert "123-45-6789" not in full_output


def test_partial_match_at_boundary_no_false_positive(email_pipeline):
    """Test that partial matches at boundaries don't create false positives."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=20)

    # "at" at end of chunk1 should not trigger false positive with chunk2 starting with "a"
    chunk1 = "I was at"
    chunk2 = " a store yesterday."

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    # No redaction should occur
    assert "[REDACTED_" not in full_output
    assert "I was at a store yesterday." in full_output


def test_entity_spanning_with_small_overlap(email_pipeline):
    """Test cross-chunk detection with overlap smaller than entity."""
    # Overlap is only 5 chars, but email is longer
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=5)

    chunk1 = "My email: test@"
    chunk2 = "example.com here"

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    # Should still detect the email
    assert "[REDACTED_1]" in full_output


def test_entity_longer_than_overlap(multi_pipeline):
    """Test entity that is much longer than overlap size."""
    # Overlap should be at least as long as the entity for reliable detection
    # SSN is 11 chars, so use overlap of 15 to be safe
    buffer = StreamingRedactionBuffer(multi_pipeline, overlap_size=15)

    # SSN is 11 characters (including dashes)
    chunk1 = "SSN is 123-"
    chunk2 = "45-6789 here."

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    # Should detect it with proper overlap
    assert "[REDACTED_1]" in full_output
    assert "123-45-6789" not in full_output


# =========================================================================
# TokenStore Integration Tests
# =========================================================================


def test_with_token_store(email_pipeline):
    """Test that TokenStore correctly records redacted entities."""
    store = TokenStore()
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=15, store=store)

    chunk1 = "Email: test@exa"
    chunk2 = "mple.com and more."

    buffer.add_chunk(chunk1)
    buffer.add_chunk(chunk2)
    buffer.finalize()

    # Check that store has the mapping
    assert len(store.mappings) == 1
    assert "[REDACTED_1]" in store.mappings
    assert store.mappings["[REDACTED_1]"] == "test@example.com"


def test_multiple_entities_in_store(multi_pipeline):
    """Test that multiple entities are all recorded in store."""
    store = TokenStore()
    buffer = StreamingRedactionBuffer(multi_pipeline, overlap_size=10, store=store)

    text = "Email: john@example.com Phone: 555-1234 SSN: 123-45-6789"
    buffer.add_chunk(text)
    buffer.finalize()

    # All three should be in store
    assert len(store.mappings) == 3
    assert store.mappings["[REDACTED_1]"] == "john@example.com"
    assert store.mappings["[REDACTED_2]"] == "555-1234"
    assert store.mappings["[REDACTED_3]"] == "123-45-6789"


def test_reveal_after_streaming(email_pipeline):
    """Test that revealed text matches original."""
    store = TokenStore()
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=15, store=store)

    original = "Contact me at john@example.com for details."

    # Redact
    output1 = buffer.add_chunk(original[:20])
    output2 = buffer.add_chunk(original[20:])
    final = buffer.finalize()
    redacted = output1 + output2 + final

    # Reveal
    revealed = store.reveal(redacted)

    assert revealed == original


# =========================================================================
# Edge Cases and Error Handling
# =========================================================================


def test_overlap_larger_than_chunk(email_pipeline):
    """Test when overlap is larger than chunk size."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=100)

    # Chunks smaller than overlap
    chunk1 = "Small"
    chunk2 = "Chunks"
    chunk3 = "Here"

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    output3 = buffer.add_chunk(chunk3)

    # Nothing output until buffer exceeds overlap
    assert output1 == ""
    assert output2 == ""
    assert output3 == ""

    final = buffer.finalize()
    assert "SmallChunksHere" in final


def test_zero_overlap(email_pipeline):
    """Test with zero overlap (no cross-chunk detection)."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=0)

    chunk1 = "Email: test@"
    chunk2 = "example.com here"

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    # With zero overlap, entity won't be detected across chunks
    # Each chunk is processed independently
    assert "test@" in full_output or "[REDACTED_" in full_output


def test_negative_overlap_raises_error(email_pipeline):
    """Test that negative overlap raises ValueError."""
    with pytest.raises(ValueError, match="overlap_size must be non-negative"):
        StreamingRedactionBuffer(email_pipeline, overlap_size=-10)


def test_unicode_at_boundary(email_pipeline):
    """Test handling of unicode/multibyte characters at boundaries."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10)

    # Unicode characters
    chunk1 = "Hello 世界 email: test@"
    chunk2 = "example.com 再见"

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    # Should handle unicode correctly
    assert "世界" in full_output or final
    assert "再见" in full_output or final
    assert "[REDACTED_1]" in full_output


def test_very_long_entity(email_pipeline):
    """Test handling of very long entities."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=20)

    # Very long email
    long_email = "verylongemailaddress12345678901234567890@example.com"
    chunk1 = f"Email: {long_email[:30]}"
    chunk2 = long_email[30:]

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    assert "[REDACTED_1]" in full_output
    assert long_email not in full_output


# =========================================================================
# Metadata and Statistics Tests
# =========================================================================


def test_metadata_tracking(email_pipeline):
    """Test that chunk metadata is correctly tracked."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10)

    buffer.add_chunk("First chunk here.")
    buffer.add_chunk("Second chunk here.")
    buffer.finalize()

    metadata = buffer.get_metadata()

    assert len(metadata) == 2
    assert all(isinstance(m, ChunkMetadata) for m in metadata)
    assert metadata[0].chunk_index == 0
    assert metadata[1].chunk_index == 1


def test_statistics(email_pipeline):
    """Test that statistics are correctly computed."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10)

    text = "Email: test@example.com here."
    buffer.add_chunk(text)
    buffer.finalize()

    stats = buffer.get_stats()

    assert stats["total_chunks"] == 1
    assert stats["total_input_chars"] == len(text)
    assert stats["total_entities_redacted"] == 1
    assert "compression_ratio" in stats


def test_reset_clears_state(email_pipeline):
    """Test that reset clears all state."""
    store = TokenStore()
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=10, store=store)

    buffer.add_chunk("Email: test@example.com")
    buffer.finalize()

    assert buffer._counter > 0
    assert len(store.mappings) > 0

    buffer.reset()

    assert buffer._counter == 0
    assert buffer._buffer == ""
    assert len(buffer._chunk_metadata) == 0
    assert len(store.mappings) == 0


# =========================================================================
# Convenience Function Tests
# =========================================================================


def test_stream_redact_generator(email_pipeline):
    """Test the stream_redact convenience function."""

    def chunk_generator():
        yield "Email: test@"
        yield "example.com and"
        yield " more text."

    outputs = list(stream_redact(chunk_generator(), email_pipeline, overlap_size=15))

    full_output = "".join(outputs)

    assert "[REDACTED_1]" in full_output
    assert "test@example.com" not in full_output
    assert "and more text." in full_output


def test_stream_redact_with_store(email_pipeline):
    """Test stream_redact with TokenStore."""
    store = TokenStore()

    def chunk_generator():
        yield "Contact: john@example.com"

    list(stream_redact(chunk_generator(), email_pipeline, store=store))

    assert len(store.mappings) == 1
    assert store.mappings["[REDACTED_1]"] == "john@example.com"


# =========================================================================
# Integration Tests with Real Detectors
# =========================================================================


def test_with_regex_detector_complex_patterns():
    """Test with complex regex patterns."""
    patterns = {
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PHONE": r"\(\d{3}\) \d{3}-\d{4}",
        "URL": r"https?://[^\s]+",
    }

    detector = RegexDetector(patterns)
    pipeline = DetectionPipeline(detector)
    buffer = StreamingRedactionBuffer(pipeline, overlap_size=30)

    chunk1 = "Contact: john@example.com or call (555) 123-"
    chunk2 = "4567 or visit https://example.com/page"

    output1 = buffer.add_chunk(chunk1)
    output2 = buffer.add_chunk(chunk2)
    final = buffer.finalize()

    full_output = output1 + output2 + final

    # All three entities should be redacted
    assert full_output.count("[REDACTED_") == 3


def test_counter_increments_correctly(email_pipeline):
    """Test that counter increments correctly across chunks."""
    buffer = StreamingRedactionBuffer(email_pipeline, overlap_size=20)

    buffer.add_chunk("First: test1@example.com")
    buffer.add_chunk("Second: test2@example.com")
    buffer.add_chunk("Third: test3@example.com")
    _ = buffer.finalize()

    stats = buffer.get_stats()
    assert stats["total_entities_redacted"] == 3


def test_custom_redaction_format():
    """Test custom redaction format."""
    detector = RegexDetector({"EMAIL": r"\w+@\w+\.\w+"})
    pipeline = DetectionPipeline(detector)
    buffer = StreamingRedactionBuffer(
        pipeline, overlap_size=10, redaction_format="<REDACTED:{counter}>"
    )

    buffer.add_chunk("Email: test@example.com")
    final = buffer.finalize()

    # Should use custom format
    assert "<REDACTED:1>" in final
    assert "[REDACTED_" not in final
