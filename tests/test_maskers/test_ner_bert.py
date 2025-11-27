import pytest
import torch
from unittest.mock import patch, MagicMock
from veildata.maskers.ner_bert import BERTNERMasker
from veildata.revealers import TokenStore


def test_berternmasker_init():
    """Test BERT NER masker initialization."""
    masker = BERTNERMasker()
    assert masker.model_name == "dslim/bert-base-NER"
    assert masker.mask_token == "[REDACTED_{counter}]"
    assert masker.store is None
    assert masker.counter == 0
    assert masker.device in ["cuda", "cpu"]


def test_berternmasker_with_store():
    """Test BERT NER masker with token store."""
    store = TokenStore()
    masker = BERTNERMasker(store=store)
    assert masker.store is store


@patch('veildata.maskers.ner_bert.AutoTokenizer.from_pretrained')
@patch('veildata.maskers.ner_bert.AutoModelForTokenClassification.from_pretrained')
def test_berternmasker_get_entity_spans(mock_model, mock_tokenizer):
    """Test entity span detection with mock model outputs."""
    # Mock tokenizer
    mock_tokenizer.return_value = MagicMock(
        **{
            'return_value': {
                'input_ids': torch.tensor([[1, 2, 3, 4]]),
                'attention_mask': torch.tensor([[1, 1, 1, 1]]),
                'offset_mapping': torch.tensor([[[0, 4], [5, 9], [10, 14], [15, 18]]]),
                'special_tokens_mask': torch.tensor([[1, 0, 0, 1]])
            },
            '_convert_id_to_token.side_effect': lambda x: f'token{x}'
        }
    )
    
    # Mock model
    mock_model.return_value = MagicMock(
        **{
            'config.id2label': {
                0: 'O',
                1: 'B-PER',
                2: 'I-PER',
                3: 'B-ORG'
            },
            'to.return_value': None,
            'eval.return_value': None
        }
    )
    
    # Mock model output
    logits = torch.zeros((1, 4, 4))  # batch_size=1, seq_len=4, num_labels=4
    logits[0, 1, 1] = 1.0  # B-PER
    logits[0, 2, 2] = 1.0  # I-PER
    mock_model.return_value.return_value = MagicMock(logits=logits)
    
    masker = BERTNERMasker()
    entities = masker._get_entity_spans("John Smith at Google")
    
    assert len(entities) == 1
    assert entities[0]['text'] == 'John Smith'
    assert entities[0]['label'] == 'PER'
    assert entities[0]['start'] == 5
    assert entities[0]['end'] == 15


def test_berternmasker_forward_no_entities():
    """Test forward pass when no entities are detected."""
    with patch.object(BERTNERMasker, '_get_entity_spans', return_value=[]):
        masker = BERTNERMasker()
        result = masker("No entities here")
        assert result == "No entities here"


def test_berternmasker_forward_with_entities():
    """Test forward pass with detected entities."""
    entities = [
        {'start': 0, 'end': 4, 'label': 'PER', 'text': 'John'},
        {'start': 14, 'end': 19, 'label': 'ORG', 'text': 'Apple'}
    ]
    
    with patch.object(BERTNERMasker, '_get_entity_spans', return_value=entities):
        store = TokenStore()
        masker = BERTNERMasker(store=store)
        result = masker("John works at Apple")

        assert "[REDACTED_1]" in result
        assert "[REDACTED_2]" in result

        # Redaction is done in reverse order
        assert store.mappings["[REDACTED_2]"] == "John"
        assert store.mappings["[REDACTED_1]"] == "Apple"


def test_berternmasker_train_mode():
    """Test train/eval mode switching."""
    masker = BERTNERMasker()
    masker.model = MagicMock()
    
    masker.train()
    masker.model.train.assert_called_once_with(True)
    
    masker.eval()
    masker.model.train.assert_called_with(False)
