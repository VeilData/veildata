from veildata.maskers.regex import RegexMasker
from veildata.revealers import TokenStore


def test_regex_masker_basic():
    """Test basic regex masking without store."""
    masker = RegexMasker(pattern=r"\b\d{3}-\d{3}-\d{4}\b")
    text = "Call me at 555-123-4567 or 555-987-6543"

    masked = masker(text)

    assert "555-123-4567" not in masked
    assert "555-987-6543" not in masked
    assert "[REDACTED_1]" in masked
    assert "[REDACTED_2]" in masked


def test_regex_masker_with_store():
    """Test regex masking with reversible token store."""
    store = TokenStore()
    masker = RegexMasker(
        pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", store=store
    )
    text = "Contact john@example.com or jane@test.org"

    masked = masker(text)

    # Original emails should be masked
    assert "john@example.com" not in masked
    assert "jane@test.org" not in masked

    # Should have redacted tokens
    assert "[REDACTED_1]" in masked
    assert "[REDACTED_2]" in masked

    # Store should have mappings
    mappings = store.mappings
    assert mappings["[REDACTED_1]"] == "john@example.com"
    assert mappings["[REDACTED_2]"] == "jane@test.org"

    # Should be able to unmask
    unmasked = store.unmask(masked)
    assert unmasked == text


def test_regex_masker_custom_token():
    """Test regex masker with custom mask token."""
    masker = RegexMasker(
        pattern=r"\bSSN-\d{3}-\d{2}-\d{4}\b", mask_token="[SSN_{counter}]"
    )
    text = "SSN-123-45-6789 and SSN-987-65-4321"

    masked = masker(text)

    assert "[SSN_1]" in masked
    assert "[SSN_2]" in masked
    assert "SSN-123-45-6789" not in masked


def test_regex_masker_no_matches():
    """Test regex masker when pattern doesn't match."""
    masker = RegexMasker(pattern=r"\b\d{3}-\d{3}-\d{4}\b")
    text = "No phone numbers here!"

    masked = masker(text)

    assert masked == text
    assert masker.counter == 0


def test_regex_masker_counter_increments():
    """Test that counter increments across multiple calls."""
    store = TokenStore()
    masker = RegexMasker(pattern=r"\d+", store=store)

    result1 = masker("First: 123")
    assert "[REDACTED_1]" in result1

    result2 = masker("Second: 456")
    assert "[REDACTED_2]" in result2

    # Both should be in store
    assert store.mappings["[REDACTED_1]"] == "123"
    assert store.mappings["[REDACTED_2]"] == "456"
