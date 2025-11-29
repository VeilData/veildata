import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from veildata.compose import Compose
from veildata.core import Module
from veildata.exceptions import ConfigMissingError
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


def load_config(config_path: Optional[str], verbose: bool = False) -> dict:
    if not config_path:
        return {}
    path = Path(config_path)
    try:
        text = path.read_text()
        if verbose:
            print(f"[veildata] Loaded config from {path.absolute()}")
    except FileNotFoundError:
        raise ConfigMissingError(f"Configuration file not found: {config_path}")

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
    method: str = "regex",
    detect_mode: str = "rules",
    config_path: Optional[str] = None,
    ml_config_path: Optional[str] = None,
    verbose: bool = False,
) -> Tuple[Module, TokenStore]:
    """
    Build a masking pipeline (Compose) and a shared TokenStore.

    Returns:
        (Module, TokenStore)
    """

    config = load_config(config_path, verbose=verbose)
    ml_config = load_config(ml_config_path, verbose=verbose)
    method = method.lower()
    store = TokenStore()

    def vprint(msg: str):
        if verbose:
            print(f"[veildata] {msg}")

    # Check if config has patterns - if so, use new detector-based approach even for rules mode
    if config.get("pattern") or config.get("patterns"):
        from veildata.detectors import (
            BertDetector,
            HybridDetector,
            RegexDetector,
            SpacyDetector,
        )
        from veildata.pipeline import DetectionPipeline

        # Support both "pattern" and "patterns" key names
        patterns = config.get("pattern") or config.get("patterns")

        if detect_mode == "rules":
            # Rules mode with patterns from config
            vprint(f"Loading RegexDetector with {len(patterns)} patterns...")
            detector = RegexDetector(patterns)
            return DetectionPipeline(detector, store=store), store

        elif detect_mode in ["ml", "hybrid"]:
            # ML/Hybrid mode
            detectors = []

            # 1. Add ML Detectors
            # ml_config can have settings at root level or nested under 'ml' key
            ml_settings = ml_config.get("ml", ml_config) if ml_config else {}
            spacy_conf = ml_settings.get("spacy", {})
            bert_conf = ml_settings.get("bert", {})

            # If no config provided, enable Spacy by default for 'ml' mode as a sane default
            if not ml_config:
                spacy_conf = {"enabled": True}

            if spacy_conf.get("enabled", False) or (
                not ml_config and detect_mode == "ml"
            ):
                vprint("Loading SpacyDetector...")
                detectors.append(
                    SpacyDetector(
                        model=spacy_conf.get("model", "en_core_web_lg"),
                        pii_labels=spacy_conf.get("pii_labels"),
                    )
                )

            if bert_conf.get("enabled", False):
                vprint("Loading BertDetector...")
                detectors.append(
                    BertDetector(
                        model_name=bert_conf.get("model_path", "dslim/bert-base-NER"),
                        threshold=bert_conf.get("threshold", 0.5),
                        label_mapping=bert_conf.get("label_mapping"),
                    )
                )

            # 2. Add Regex Detector for Hybrid mode
            if detect_mode == "hybrid":
                vprint("Loading RegexDetector for Hybrid mode...")
                detectors.append(RegexDetector(patterns))

            if not detectors:
                raise ValueError("No detectors enabled for ML/Hybrid mode.")

            if len(detectors) > 1:
                vprint(f"Combining {len(detectors)} detectors in Hybrid mode...")
                hybrid_conf = config.get("options", {}).get("hybrid", {})
                detector = HybridDetector(
                    detectors,
                    strategy=hybrid_conf.get("strategy", "union"),
                    prefer=hybrid_conf.get("prefer", "ml"),
                )
            else:
                detector = detectors[0]

            return DetectionPipeline(detector, store=store), store

    # Legacy / Rules Mode (no patterns in config)
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
    return store.unmask
