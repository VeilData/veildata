from veildata.core import Module
from veildata.revealers import TokenStore

try:
    import spacy
except ImportError as e:
    raise ImportError(
        "spaCy is not installed. Install with: `pip install veildata[spacy]`"
    ) from e


class SpacyNERMasker(Module):
    """Mask named entities in text using a spaCy model, with optional reversible tracking."""

    def __init__(
        self,
        model: str = "en_core_web_sm",
        entities: list[str] | None = None,
        mask_token: str = "[REDACTED]",
        store: TokenStore | None = None,
    ) -> None:
        super().__init__()
        self.model_name = model
        self.entities = set(entities or ["PERSON", "ORG", "GPE", "EMAIL", "PHONE"])
        self.mask_token = mask_token
        self.store = store
        self._load_model()
        self.counter = 0

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
                self.counter += 1
                token = f"{self.mask_token}_{self.counter}"
                if self.store:
                    self.store.record(token, ent.text)
                redacted = redacted[: ent.start_char] + token + redacted[ent.end_char :]
        return redacted
