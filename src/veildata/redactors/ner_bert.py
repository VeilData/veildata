import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from veildata.core import Module
from veildata.revealers import TokenStore


class BERTNERRedactor(Module):
    """Redact named entities in text using a fine-tuned BERT NER model."""

    def __init__(
        self,
        model_name: str = "dslim/bert-base-NER",
        redaction_token: str = "[REDACTED_{counter}]",
        store: TokenStore | None = None,
        device: str | None = None,
        use_fp16: bool = False,
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.redaction_token = redaction_token
        self.store = store
        self.counter = 0
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.use_fp16 = use_fp16 and self.device != "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.model.to(self.device)

        # Enable eval mode for inference (faster, disables dropout)
        self.model.eval()

        # Enable FP16 for GPU if requested (2x speedup, half memory)
        if self.use_fp16:
            self.model = self.model.half()

        self.label_map = self.model.config.id2label

    def _get_entity_spans(self, text: str) -> list:
        """Get entity spans from text using the BERT NER model."""
        # Get tokenization with character offsets
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            return_offsets_mapping=True,
            truncation=True,
            return_special_tokens_mask=True,
        )

        # Create model inputs without the extra fields
        model_inputs = {
            "input_ids": inputs["input_ids"].to(self.device),
            "attention_mask": inputs["attention_mask"].to(self.device),
        }

        with torch.inference_mode():
            outputs = self.model(**model_inputs)

        # Get predictions and token information
        predictions = torch.argmax(outputs.logits, dim=2)[0].cpu().numpy()
        input_ids = inputs["input_ids"][0].cpu().numpy()
        offset_mapping = inputs["offset_mapping"][0].cpu().numpy()
        special_tokens_mask = inputs["special_tokens_mask"][0].cpu().numpy()

        # Convert to human-readable labels
        labels = [self.label_map[pred] for pred in predictions]

        # Group tokens into entities
        entities = []
        current_entity = None

        for i, (token_id, label, (start, end), is_special) in enumerate(
            zip(input_ids, labels, offset_mapping, special_tokens_mask)
        ):
            if is_special:  # Skip special tokens like [CLS], [SEP]
                continue

            token = self.tokenizer.convert_tokens_to_string(
                [self.tokenizer._convert_id_to_token(token_id)]
            )

            if label.startswith("B-"):
                if current_entity is not None:
                    entities.append(current_entity)
                current_entity = {
                    "start": start,
                    "end": end,
                    "label": label[2:],  # Remove B- or I- prefix
                    "text": token,
                }
            elif label.startswith("I-") and current_entity is not None:
                # Continue current entity
                current_entity["end"] = end
                current_entity["text"] += token.replace("##", "")
            else:
                if current_entity is not None:
                    entities.append(current_entity)
                    current_entity = None

        if current_entity is not None:  # Add the last entity if exists
            entities.append(current_entity)

        return entities

    def forward(self, text: str) -> str:
        """Redact entities using model predictions."""
        entities = self._get_entity_spans(text)
        if not entities:
            return text

        # Sort entities by start position (in reverse order for easier replacement)
        entities.sort(key=lambda x: x["start"], reverse=True)

        result = list(text)

        for entity in entities:
            start = entity["start"]
            end = entity["end"]
            entity_text = text[start:end]

            # Skip if the entity text doesn't match (can happen due to tokenization quirks)
            if entity_text.strip() != entity["text"].strip():
                continue

            # Generate redaction token and record in store
            self.counter += 1
            mask = self.redaction_token.format(counter=self.counter)
            if self.store:
                self.store.record(mask, entity_text)

            # Replace the entity text with the mask
            result[start:end] = [mask] + [""] * (end - start - len(mask))

        return "".join(result)

    def train(self, mode: bool = True) -> "BERTNERRedactor":
        """Toggle train/eval mode on BERT model."""
        super().train(mode)
        self.model.train(mode)
        return self
