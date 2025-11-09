import spacy

from src.veildata.core import Module


class SpacyNERMasker(Module):
    """Mask named entities in text using a spaCy model."""

    def __init__(
        self,
        model: str = "en_core_web_sm",
        entities: list[str] | None = None,
        mask_token: str = "[REDACTED]",
    ) -> None:
        super().__init__()
        self.model_name = model
        self.entities = set(entities or ["PERSON", "ORG", "GPE", "EMAIL", "PHONE"])
        self.mask_token = mask_token
        self._load_model()

    def _load_model(self) -> None:
        try:
            self.nlp = spacy.load(self.model_name, disable=["parser", "tagger"])
        except OSError:
            raise RuntimeError(
                f"spaCy model '{self.model_name}' not found. "
                f"Run: python -m spacy download {self.model_name}"
            )

    def forward(self, text: str) -> str:
        doc = self.nlp(text)
        redacted = text
        for ent in reversed(doc.ents):
            if ent.label_ in self.entities:
                redacted = (
                    redacted[: ent.start_char]
                    + self.mask_token
                    + redacted[ent.end_char :]
                )
        return redacted

    def train(self, mode: bool = True) -> "SpacyNERMasker":
        """Toggle training mode on spaCy pipeline."""
        super().train(mode)
        self.nlp.training = mode
        return self
