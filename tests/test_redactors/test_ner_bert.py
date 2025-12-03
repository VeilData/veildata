"""Tests for BERTNERRedactor to achieve 100% coverage."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import torch

from veildata.redactors.ner_bert import BERTNERRedactor
from veildata.revealers import TokenStore


@pytest.fixture
def mock_model_and_tokenizer():
    """Mock transformers components to avoid downloading real models."""
    with (
        patch("veildata.redactors.ner_bert.AutoTokenizer") as mock_tokenizer_class,
        patch(
            "veildata.redactors.ner_bert.AutoModelForTokenClassification"
        ) as mock_model_class,
    ):
        # Mock tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        # Mock model
        mock_model = MagicMock()
        mock_model.config.id2label = {0: "O", 1: "B-PER", 2: "I-PER", 3: "B-ORG"}
        mock_model_class.from_pretrained.return_value = mock_model

        yield mock_tokenizer, mock_model, mock_tokenizer_class, mock_model_class


def test_init_default(mock_model_and_tokenizer):
    """Test BERTNERRedactor initialization with default parameters."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    assert redactor.model_name == "dslim/bert-base-NER"
    assert redactor.redaction_token == "[REDACTED_{counter}]"
    assert redactor.store is None
    assert redactor.counter == 0
    assert redactor.device in ["cpu", "cuda"]
    assert redactor.use_fp16 is False


def test_init_custom_model(mock_model_and_tokenizer):
    """Test BERTNERRedactor with custom model name."""
    redactor = BERTNERRedactor(model_name="custom/model")
    assert redactor.model_name == "custom/model"


def test_init_with_store(mock_model_and_tokenizer):
    """Test BERTNERRedactor with TokenStore."""
    store = TokenStore()
    redactor = BERTNERRedactor(store=store)
    assert redactor.store is store


def test_init_custom_redaction_token(mock_model_and_tokenizer):
    """Test BERTNERRedactor with custom mask token."""
    redactor = BERTNERRedactor(redaction_token="<MASKED_{counter}>")
    assert redactor.redaction_token == "<MASKED_{counter}>"


def test_init_explicit_cpu_device(mock_model_and_tokenizer):
    """Test BERTNERRedactor with explicit CPU device."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor(device="cpu")

    assert redactor.device == "cpu"
    assert redactor.use_fp16 is False  # FP16 disabled on CPU
    mock_model.to.assert_called_with("cpu")


@patch("torch.cuda.is_available", return_value=True)
def test_init_gpu_auto_detect(mock_cuda, mock_model_and_tokenizer):
    """Test BERTNERRedactor auto-detects GPU when available."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    assert redactor.device == "cuda"


@patch("torch.cuda.is_available", return_value=False)
def test_init_cpu_auto_detect(mock_cuda, mock_model_and_tokenizer):
    """Test BERTNERRedactor auto-detects CPU when GPU not available."""
    redactor = BERTNERRedactor()
    assert redactor.device == "cpu"


@patch("torch.cuda.is_available", return_value=True)
def test_init_fp16_enabled_on_gpu(mock_cuda, mock_model_and_tokenizer):
    """Test BERTNERRedactor enables FP16 on GPU."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor(device="cuda", use_fp16=True)

    assert redactor.use_fp16 is True
    mock_model.half.assert_called_once()


def test_init_fp16_disabled_on_cpu(mock_model_and_tokenizer):
    """Test BERTNERRedactor disables FP16 on CPU even if requested."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor(device="cpu", use_fp16=True)

    assert redactor.use_fp16 is False
    mock_model.half.assert_not_called()


def test_init_eval_mode_enabled(mock_model_and_tokenizer):
    """Test BERTNERRedactor sets model to eval mode."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    _ = BERTNERRedactor()

    mock_model.eval.assert_called_once()


def test_forward_no_entities(mock_model_and_tokenizer):
    """Test forward pass when no entities are detected."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer
    redactor = BERTNERRedactor()

    # Mock _get_entity_spans to return no entities
    redactor._get_entity_spans = MagicMock(return_value=[])

    text = "This text has no entities."
    result = redactor(text)

    assert result == text
    assert redactor.counter == 0


def test_forward_with_entities(mock_model_and_tokenizer):
    """Test forward pass with entities detected."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer
    redactor = BERTNERRedactor()

    # Mock _get_entity_spans
    redactor._get_entity_spans = MagicMock(
        return_value=[
            {"start": 0, "end": 4, "label": "PER", "text": "John"},
            {"start": 14, "end": 23, "label": "ORG", "text": "Microsoft"},
        ]
    )

    text = "John works at Microsoft."
    result = redactor(text)

    assert result == "[REDACTED_2] works at [REDACTED_1]."
    assert redactor.counter == 2


def test_forward_with_store(mock_model_and_tokenizer):
    """Test forward pass records entities in store."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer
    store = TokenStore()
    redactor = BERTNERRedactor(store=store)

    # Mock _get_entity_spans
    redactor._get_entity_spans = MagicMock(
        return_value=[{"start": 0, "end": 4, "label": "PER", "text": "John"}]
    )

    text = "John is here."
    result = redactor(text)

    assert "[REDACTED_1]" in result
    assert store.mappings["[REDACTED_1]"] == "John"


def test_forward_entity_text_mismatch(mock_model_and_tokenizer):
    """Test forward pass skips entities with text mismatch."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer
    redactor = BERTNERRedactor()

    # Mock entity with text that doesn't match the actual text
    redactor._get_entity_spans = MagicMock(
        return_value=[{"start": 0, "end": 4, "label": "PER", "text": "Wrong"}]
    )

    text = "John is here."
    result = redactor(text)

    # Should skip the entity due to mismatch
    assert result == text
    assert redactor.counter == 0


def test_forward_counter_increments(mock_model_and_tokenizer):
    """Test counter increments correctly across multiple calls."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer
    redactor = BERTNERRedactor()

    redactor._get_entity_spans = MagicMock(
        return_value=[{"start": 0, "end": 4, "label": "PER", "text": "John"}]
    )

    text = "John is here."
    redactor(text)
    assert redactor.counter == 1

    redactor(text)
    assert redactor.counter == 2


def test_get_entity_spans_basic(mock_model_and_tokenizer):
    """Test _get_entity_spans with basic entity detection."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    # Mock tokenizer outputs
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[101, 2198, 102]]),  # [CLS] John [SEP]
        "attention_mask": torch.tensor([[1, 1, 1]]),
        "offset_mapping": torch.tensor([[(0, 0), (0, 4), (0, 0)]]),  # CLS, token, SEP
        "special_tokens_mask": torch.tensor([[1, 0, 1]]),  # special, normal, special
    }

    # Mock model predictions
    mock_logits = torch.zeros((1, 3, 4))  # batch, seq, num_labels
    mock_logits[0, 1, 1] = 10.0  # B-PER for token at position 1
    mock_output = Mock()
    mock_output.logits = mock_logits
    mock_model.return_value = mock_output

    # Mock tokenizer methods
    mock_tokenizer._convert_id_to_token.return_value = "John"
    mock_tokenizer.convert_tokens_to_string.return_value = "John"

    entities = redactor._get_entity_spans("John")

    assert len(entities) == 1
    assert entities[0]["label"] == "PER"
    assert entities[0]["text"] == "John"


def test_get_entity_spans_no_entities(mock_model_and_tokenizer):
    """Test _get_entity_spans when no entities detected."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    # Mock tokenizer outputs with no entities
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[101, 2023, 102]]),
        "attention_mask": torch.tensor([[1, 1, 1]]),
        "offset_mapping": torch.tensor([[(0, 0), (0, 4), (0, 0)]]),
        "special_tokens_mask": torch.tensor([[1, 0, 1]]),
    }

    # Mock model predictions - all O (non-entity)
    mock_logits = torch.zeros((1, 3, 4))
    mock_logits[0, :, 0] = 10.0  # All tokens labeled as "O"
    mock_output = Mock()
    mock_output.logits = mock_logits
    mock_model.return_value = mock_output

    entities = redactor._get_entity_spans("text")

    assert len(entities) == 0


def test_get_entity_spans_continuation(mock_model_and_tokenizer):
    """Test _get_entity_spans handles I- prefix continuation."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    # Mock two-token entity: "John" "Smith"
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[101, 2198, 3044, 102]]),  # [CLS] John Smith [SEP]
        "attention_mask": torch.tensor([[1, 1, 1, 1]]),
        "offset_mapping": torch.tensor([[(0, 0), (0, 4), (5, 10), (0, 0)]]),
        "special_tokens_mask": torch.tensor([[1, 0, 0, 1]]),
    }

    # Mock model predictions: B-PER, I-PER
    mock_logits = torch.zeros((1, 4, 4))
    mock_logits[0, 1, 1] = 10.0  # B-PER
    mock_logits[0, 2, 2] = 10.0  # I-PER
    mock_output = Mock()
    mock_output.logits = mock_logits
    mock_model.return_value = mock_output

    # Mock tokenizer methods
    call_count = [0]

    def mock_convert_id_to_token(token_id):
        tokens = ["John", "Smith"]
        result = tokens[call_count[0]]
        call_count[0] += 1
        return result

    def mock_convert_tokens_to_string(tokens):
        return tokens[0]

    mock_tokenizer._convert_id_to_token.side_effect = mock_convert_id_to_token
    mock_tokenizer.convert_tokens_to_string.side_effect = mock_convert_tokens_to_string

    entities = redactor._get_entity_spans("John Smith")

    assert len(entities) == 1
    assert entities[0]["label"] == "PER"
    assert "John" in entities[0]["text"]
    assert entities[0]["end"] == 10


def test_get_entity_spans_end_entity(mock_model_and_tokenizer):
    """Test _get_entity_spans handles entity at end of sequence."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    # Entity ending right before [SEP]
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[101, 2198, 102]]),
        "attention_mask": torch.tensor([[1, 1, 1]]),
        "offset_mapping": torch.tensor([[(0, 0), (0, 4), (0, 0)]]),
        "special_tokens_mask": torch.tensor([[1, 0, 1]]),
    }

    mock_logits = torch.zeros((1, 3, 4))
    mock_logits[0, 1, 1] = 10.0  # B-PER at position 1
    mock_output = Mock()
    mock_output.logits = mock_logits
    mock_model.return_value = mock_output

    mock_tokenizer._convert_id_to_token.return_value = "John"
    mock_tokenizer.convert_tokens_to_string.return_value = "John"

    entities = redactor._get_entity_spans("John")

    # Should capture the entity even though it's at the end
    assert len(entities) == 1


def test_get_entity_spans_multiple_separate_entities(mock_model_and_tokenizer):
    """Test _get_entity_spans with multiple separate entities."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    # "John" O O "Microsoft"
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[101, 2198, 2003, 2012, 3044, 102]]),
        "attention_mask": torch.tensor([[1, 1, 1, 1, 1, 1]]),
        "offset_mapping": torch.tensor(
            [[(0, 0), (0, 4), (5, 7), (8, 10), (11, 20), (0, 0)]]
        ),
        "special_tokens_mask": torch.tensor([[1, 0, 0, 0, 0, 1]]),
    }

    # B-PER at pos 1, B-ORG at pos 4
    mock_logits = torch.zeros((1, 6, 4))
    mock_logits[0, 1, 1] = 10.0  # B-PER
    mock_logits[0, 4, 3] = 10.0  # B-ORG
    mock_output = Mock()
    mock_output.logits = mock_logits
    mock_model.return_value = mock_output

    call_count = [0]

    def mock_convert_id_to_token(token_id):
        tokens = ["John", "is", "at", "Microsoft"]
        result = tokens[call_count[0]] if call_count[0] < len(tokens) else "word"
        call_count[0] += 1
        return result

    mock_tokenizer._convert_id_to_token.side_effect = mock_convert_id_to_token
    mock_tokenizer.convert_tokens_to_string.side_effect = lambda x: x[0]

    entities = redactor._get_entity_spans("John is at Microsoft")

    assert len(entities) == 2
    assert entities[0]["label"] == "PER"
    assert entities[1]["label"] == "ORG"


def test_train_mode_toggle(mock_model_and_tokenizer):
    """Test train() method toggles model mode."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer

    redactor = BERTNERRedactor()

    # Reset the mock to clear the eval() call from __init__
    mock_model.train.reset_mock()

    # Test enabling training mode
    result = redactor.train(True)

    mock_model.train.assert_called_with(True)
    assert result is redactor  # Returns self

    # Test disabling training mode (back to eval)
    mock_model.train.reset_mock()
    redactor.train(False)

    mock_model.train.assert_called_with(False)


def test_forward_empty_text(mock_model_and_tokenizer):
    """Test forward with empty text."""
    mock_tokenizer, mock_model, _, _ = mock_model_and_tokenizer
    redactor = BERTNERRedactor()

    redactor._get_entity_spans = MagicMock(return_value=[])

    result = redactor("")
    assert result == ""
