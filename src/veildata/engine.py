import json
from typing import Dict, List, Optional, Type

import yaml

from veildata.maskers.ner_bert import BERTNERMasker
from veildata.maskers.ner_spacy import SpacyNERMasker
from veildata.maskers.regex import RegexMasker
from veildata.revealers import TokenStore

MASKER_REGISTRY: Dict[str, Type] = {
    "regex": RegexMasker,
    "ner_spacy": SpacyNERMasker,
    "ner_bert": BERTNERMasker,
}


def list_available_maskers() -> List[str]:
    """Return the available registered masking methods."""
    return list(MASKER_REGISTRY.keys()) + ["all"]


def load_config(config_path: Optional[str]) -> Optional[dict]:
    if not config_path:
        return None
    with open(config_path, "r") as f:
        if config_path.endswith(".json"):
            return json.load(f)
        return yaml.safe_load(f)


def build_masker(method: str, config_path: Optional[str] = None, verbose: bool = False):
    """Factory to create a masker based on the method name."""
    config = load_config(config_path)
    method = method.lower()

    if method == "all":
        return CompositeMasker(
            [
                RegexMasker(**config),
                SpacyNERMasker(**config),
                BERTNERMasker(**config),
            ]
        )

    if method not in MASKER_REGISTRY:
        raise ValueError(
            f"Unknown masking method '{method}'. "
            f"Available: {', '.join(list_available_maskers())}"
        )

    masker_cls = MASKER_REGISTRY[method]
    return masker_cls(config, verbose=verbose)


def build_unmasker(store_path: str):
    """
    Build a callable unmasker using a saved TokenStore mapping.

    Args:
        store_path: Path to a JSON file created by TokenStore.save().

    Returns:
        A callable that takes masked text and returns unmasked text.
    """
    store = TokenStore.load(store_path)
    return store.unmask


class CompositeMasker:
    """Apply multiple maskers sequentially."""

    def __init__(self, maskers: List):
        self.maskers = maskers

    def mask(self, text: str, dry_run: bool = False) -> str:
        for masker in self.maskers:
            text = masker.mask(text, dry_run=dry_run)
        return text


class Unmasker:
    """Simple reversible unmasking utility."""

    def __init__(self, mapping_path: Optional[str] = None):
        self.mapping = {}
        if mapping_path:
            with open(mapping_path, "r") as f:
                self.mapping = json.load(f)

    def unmask(self, text: str) -> str:
        for token, original in self.mapping.items():
            text = text.replace(token, original)
        return text
