from unittest.mock import MagicMock, patch

from veildata.redactors.ner_spacy import SpacyNERRedactor
from veildata.revealers import TokenStore


@patch("veildata.redactors.ner_spacy.spacy")
def test_ner_spacy_init(mock_spacy):
    """Test SpacyNERRedactor initialization."""
    # Setup mock
    mock_nlp = MagicMock()
    mock_spacy.load.return_value = mock_nlp

    redactor = SpacyNERRedactor()
    assert redactor.entities == set(("PERSON", "ORG", "GPE", "EMAIL", "PHONE"))
    assert redactor.model_name == "en_core_web_sm"
    assert redactor.store is None

    # Verify load was called
    mock_spacy.load.assert_called_with("en_core_web_sm", disable=["parser", "tagger"])


@patch("veildata.redactors.ner_spacy.spacy")
def test_ner_spacy_with_custom_entities(mock_spacy):
    """Test SpacyNERRedactor with custom entities."""
    mock_spacy.load.return_value = MagicMock()

    redactor = SpacyNERRedactor(entities=["PERSON", "ORG"])
    assert redactor.entities == set(("PERSON", "ORG"))


@patch("veildata.redactors.ner_spacy.spacy")
def test_ner_spacy_with_store(mock_spacy):
    """Test SpacyNERRedactor with token store."""
    mock_spacy.load.return_value = MagicMock()

    store = TokenStore()
    redactor = SpacyNERRedactor(store=store)
    assert redactor.store is store


@patch("veildata.redactors.ner_spacy.spacy")
def test_ner_spacy_forward(mock_spacy):
    """Test SpacyNERRedactor forward pass with mock spaCy model."""
    # Mock spaCy model and doc
    mock_nlp = MagicMock()
    mock_spacy.load.return_value = mock_nlp

    # Mock entity
    mock_ent = MagicMock()
    mock_ent.label_ = "PERSON"
    mock_ent.start_char = 0
    mock_ent.end_char = 4
    mock_ent.text = "John"

    # Mock doc
    mock_doc = MagicMock()
    mock_doc.ents = [mock_ent]
    mock_nlp.return_value = mock_doc

    redactor = SpacyNERRedactor(entities=["PERSON"])
    result = redactor("John works at Apple")

    assert "[REDACTED_1]" in result
    assert "Apple" in result  # Not in our entities list


@patch("veildata.redactors.ner_spacy.spacy")
def test_ner_spacy_forward_no_entities(mock_spacy):
    """Test SpacyNERRedactor when no entities are found."""
    mock_nlp = MagicMock()
    mock_spacy.load.return_value = mock_nlp
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp.return_value = mock_doc

    redactor = SpacyNERRedactor()
    result = redactor("No entities here")
    assert result == "No entities here"


@patch("veildata.redactors.ner_spacy.spacy")
def test_ner_spacy_with_store_integration(mock_spacy):
    """Test SpacyNERRedactor with store integration."""
    # Setup mock
    mock_nlp = MagicMock()
    mock_spacy.load.return_value = mock_nlp

    # Mock entity
    mock_ent = MagicMock()
    mock_ent.label_ = "PERSON"
    mock_ent.start_char = 7
    mock_ent.end_char = 11
    mock_ent.text = "John"

    # Mock doc
    mock_doc = MagicMock()
    mock_doc.ents = [mock_ent]
    mock_nlp.return_value = mock_doc

    # Test with store
    store = TokenStore()
    redactor = SpacyNERRedactor(entities=["PERSON"], store=store)
    result = redactor("Hello, John!")

    assert "[REDACTED_1]" in result
    assert store.mappings["[REDACTED_1]"] == "John"
    assert store.reveal(result) == "Hello, John!"
