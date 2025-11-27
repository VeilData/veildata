from unittest.mock import MagicMock, patch

from veildata.maskers.ner_spacy import SpacyNERMasker
from veildata.revealers import TokenStore


def test_ner_spacy_init():
    """Test SpacyNERMasker initialization."""
    masker = SpacyNERMasker()
    assert masker.entities == set(("PERSON", "ORG", "GPE", "EMAIL", "PHONE"))
    assert masker.model_name == "en_core_web_sm"
    assert masker.store is None


def test_ner_spacy_with_custom_entities():
    """Test SpacyNERMasker with custom entities."""
    masker = SpacyNERMasker(entities=["PERSON", "ORG"])
    assert masker.entities == set(("PERSON", "ORG"))


def test_ner_spacy_with_store():
    """Test SpacyNERMasker with token store."""
    store = TokenStore()
    masker = SpacyNERMasker(store=store)
    assert masker.store is store


@patch("veildata.maskers.ner_spacy.spacy")
def test_ner_spacy_forward(mock_spacy):
    """Test SpacyNERMasker forward pass with mock spaCy model."""
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

    masker = SpacyNERMasker(entities=["PERSON"])
    result = masker("John works at Apple")

    assert "[REDACTED_1]" in result
    assert "Apple" in result  # Not in our entities list


def test_ner_spacy_forward_no_entities():
    """Test SpacyNERMasker when no entities are found."""
    with patch("veildata.maskers.ner_spacy.spacy") as mock_spacy:
        mock_nlp = MagicMock()
        mock_spacy.load.return_value = mock_nlp
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_nlp.return_value = mock_doc

        masker = SpacyNERMasker()
        result = masker("No entities here")
        assert result == "No entities here"


def test_ner_spacy_with_store_integration():
    """Test SpacyNERMasker with store integration."""
    with patch("veildata.maskers.ner_spacy.spacy") as mock_spacy:
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
        masker = SpacyNERMasker(entities=["PERSON"], store=store)
        result = masker("Hello, John!")

        assert "[REDACTED_1]" in result
        assert store.mappings["[REDACTED_1]"] == "John"
        assert store.unmask(result) == "Hello, John!"
