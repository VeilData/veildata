import json
from pathlib import Path
from typing import Dict


class TokenStore:
    """
    A reversible token store that maps redacted tokens back to original values.

    Example:
        store = TokenStore()
        store.record("[REDACTED_1]", "john.doe@example.com")
        text = store.unmask("Contact [REDACTED_1]")
    """

    def __init__(self) -> None:
        self._mapping: Dict[str, str] = {}

    def record(self, token: str, original: str) -> None:
        """Record a mapping between a redacted token and its original value."""
        self._mapping[token] = original

    def bulk_record(self, mappings: Dict[str, str]) -> None:
        """Add multiple mappings at once."""
        self._mapping.update(mappings)

    def unmask(self, text: str) -> str:
        """Replace all stored tokens with their original values in text."""
        for token, original in self._mapping.items():
            text = text.replace(token, original)
        return text

    def clear(self) -> None:
        """Reset the store."""
        self._mapping.clear()

    @property
    def mappings(self) -> Dict[str, str]:
        """Return a copy of the internal mapping."""
        return dict(self._mapping)

    def save(self, path: str):
        Path(path).write_text(json.dumps(self.mappings, indent=2))

    @classmethod
    def load(cls, path: str):
        store = cls()
        store._mapping = json.loads(Path(path).read_text())
        return store
