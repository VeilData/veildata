from veildata.redactors.regex import RegexRedactor
from veildata.revealers import TokenStore


def test_regex_redactor_basic():
    """Test basic regex redaction without store."""
    redactor = RegexRedactor(pattern=r"\b\d{3}-\d{3}-\d{4}\b")
    text = "Call me at 555-123-4567 or 555-987-6543"

    redacted = redactor(text)

    assert "555-123-4567" not in redacted
    assert "555-987-6543" not in redacted
    assert "[REDACTED_1]" in redacted
    assert "[REDACTED_2]" in redacted


def test_regex_redactor_with_store():
    """Test regex redaction with reversible token store."""
    store = TokenStore()
    redactor = RegexRedactor(
        pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", store=store
    )
    text = "Contact john@example.com or jane@test.org"

    redacted = redactor(text)

    # Original emails should be redacted
    assert "john@example.com" not in redacted
    assert "jane@test.org" not in redacted

    # Should have redacted tokens
    assert "[REDACTED_1]" in redacted
    assert "[REDACTED_2]" in redacted

    # Store should have mappings
    mappings = store.mappings
    assert mappings["[REDACTED_1]"] == "john@example.com"
    assert mappings["[REDACTED_2]"] == "jane@test.org"

    # Should be able to reveal
    revealed = store.reveal(redacted)
    assert revealed == text


def test_regex_redactor_custom_token():
    """Test regex redactor with custom redaction token."""
    redactor = RegexRedactor(
        pattern=r"\bSSN-\d{3}-\d{2}-\d{4}\b", redaction_token="[SSN_{counter}]"
    )
    text = "SSN-123-45-6789 and SSN-987-65-4321"

    redacted = redactor(text)

    assert "[SSN_1]" in redacted
    assert "[SSN_2]" in redacted
    assert "SSN-123-45-6789" not in redacted


def test_regex_redactor_no_matches():
    """Test regex redactor when pattern doesn't match."""
    redactor = RegexRedactor(pattern=r"\b\d{3}-\d{3}-\d{4}\b")
    text = "No phone numbers here!"

    redacted = redactor(text)

    assert redacted == text
    assert redactor.counter == 0


def test_regex_redactor_counter_increments():
    """Test that counter increments across multiple calls."""
    store = TokenStore()
    redactor = RegexRedactor(pattern=r"\d+", store=store)

    result1 = redactor("First: 123")
    assert "[REDACTED_1]" in result1

    result2 = redactor("Second: 456")
    assert "[REDACTED_2]" in result2

    # Both should be in store
    assert store.mappings["[REDACTED_1]"] == "123"
    assert store.mappings["[REDACTED_2]"] == "456"
