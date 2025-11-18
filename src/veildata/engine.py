import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from veildata.compose import Compose
from veildata.revealers import TokenStore

MASKER_REGISTRY: Dict[str, str] = {
    "regex": "veildata.maskers.regex.RegexMasker",
    "ner_spacy": "veildata.maskers.ner_spacy.SpacyNERMasker",
    "ner_bert": "veildata.maskers.ner_bert.BERTNERMasker",
}


def list_available_maskers() -> List[str]:
    """Return available masking engines."""
    return list(MASKER_REGISTRY.keys()) + ["all"]


def list_engines():
    return [
        ("regex", "Pattern-based masking (fast, deterministic)."),
        ("spacy", "NER-based entity detection."),
        ("hybrid", "Regex + NER combined."),
    ]


def load_config(config_path: Optional[str]) -> dict:
    if not config_path:
        return {}
    path = Path(config_path)
    text = path.read_text()
    if config_path.endswith(".json"):
        return json.loads(text)
    return yaml.safe_load(text)


def _lazy_import(dotted_path: str):
    """
    Import a class by dotted string path:
    e.g. "veildata.maskers.regex.RegexMasker"
    """
    module_path, cls_name = dotted_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[cls_name])
    return getattr(module, cls_name)


def build_masker(
    method: str,
    config_path: Optional[str] = None,
    verbose: bool = False,
) -> Tuple[Compose, TokenStore]:
    """
    Build a masking pipeline (Compose) and a shared TokenStore.

    Returns:
        (Compose(maskers), TokenStore)
    """
    config = load_config(config_path)
    method = method.lower()
    store = TokenStore()

    def vprint(msg: str):
        if verbose:
            print(f"[veildata] {msg}")

    if method == "all":
        maskers = []
        for key, dotted_path in MASKER_REGISTRY.items():
            cls = _lazy_import(dotted_path)
            vprint(f"Loading masker: {key}")
            maskers.append(cls(store=store, **config))
        return Compose(maskers), store

    if method not in MASKER_REGISTRY:
        raise ValueError(
            f"Unknown masking method '{method}'. "
            f"Available: {', '.join(list_available_maskers())}"
        )

    cls_path = MASKER_REGISTRY[method]
    cls = _lazy_import(cls_path)
    vprint(f"Loading masker: {method}")

    masker = cls(store=store, **config)
    return Compose([masker]), store


def build_unmasker(store_path: str):
    """
    Build a callable unmasker from a saved TokenStore mapping.

    Returns:
        callable(text: str) -> str
    """
    store = TokenStore.load(store_path)
    return store.unmask
