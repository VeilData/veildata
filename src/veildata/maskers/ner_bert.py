import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from src.veildata.core import Module


class BERTNERMasker(Module):
    """Mask named entities in text using a fine-tuned BERT NER model."""

    def __init__(
        self,
        model_name: str = "dslim/bert-base-NER",
        mask_token: str = "[REDACTED]",
        device: str | None = None,
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.mask_token = mask_token
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.label_map = self.model.config.id2label

    def forward(self, text: str) -> str:
        """Redact entities using model predictions."""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(
            self.device
        )
        with torch.no_grad():
            outputs = self.model(**inputs)

        predictions = torch.argmax(outputs.logits, dim=2)[0].tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

        redacted_tokens = []
        for token, pred_id in zip(tokens, predictions):
            label = self.label_map[pred_id]
            if label.startswith("B-") or label.startswith("I-"):
                redacted_tokens.append(self.mask_token)
            else:
                redacted_tokens.append(token)

        redacted_text = self.tokenizer.convert_tokens_to_string(redacted_tokens)
        return redacted_text.replace(" ##", "")

    def train(self, mode: bool = True) -> "BERTNERMasker":
        """Toggle train/eval mode on BERT model."""
        super().train(mode)
        self.model.train(mode)
        return self
