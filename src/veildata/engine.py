from typing import Dict, List, Optional, Tuple

from veildata.compose import Compose
from veildata.core import Module
from veildata.core.config import VeilConfig, load_config
from veildata.revealers import TokenStore

REDACTOR_REGISTRY: Dict[str, str] = {
    "regex": "veildata.redactors.regex.RegexRedactor",
    "ner_spacy": "veildata.redactors.ner_spacy.SpacyNERRedactor",
    "ner_bert": "veildata.redactors.ner_bert.BERTNERRedactor",
}


def list_available_redactors() -> List[str]:
    """Return available redaction engines."""
    return list(REDACTOR_REGISTRY.keys()) + ["all"]


def list_engines():
    return [
        ("regex", "Pattern-based redaction (fast, deterministic)."),
        ("spacy", "NER-based entity detection."),
        ("hybrid", "Regex + NER combined."),
    ]


def _lazy_import(dotted_path: str):
    """
    Import a class by dotted string path:
    e.g. "veildata.redactors.regex.RegexRedactor"
    """
    module_path, cls_name = dotted_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[cls_name])
    return getattr(module, cls_name)


def build_redactor(
    method: str = "regex",
    detect_mode: str = "rules",
    config_path: Optional[str] = None,
    ml_config_path: Optional[str] = None,
    verbose: bool = False,
    config: Optional[VeilConfig] = None,
) -> Tuple[Module, TokenStore]:
    """
    Factory function to build a redactor based on configuration.
    """

    def vprint(msg: str):
        if verbose:
            print(f"[veildata] {msg}")

    # Load main config if not provided
    if config is None:
        # If config_path is explicitly provided, use it
        # Otherwise load_config will look for defaults
        config = load_config(config_path, verbose=verbose)

    # Update method from config if not explicitly overridden by CLI (which usually defaults to "regex")
    # Note: CLI handling logic usually passes explicit method args, but we respect config if method is default
    if method == "regex" and config.method != "regex":
        method = config.method.value

    # Merge ML config if separate file provided (Legacy support)
    if ml_config_path:
        _ = load_config(ml_config_path, verbose=verbose)
        # We would need to merge this into the main config object,
        # but for now we assume modern usage uses a single config.
        # This is a simplification during the refactor.
        pass

    store = TokenStore()

    # Check for patterns
    start_patterns = config.get_patterns()

    if start_patterns:
        from veildata.detectors import (
            BertDetector,
            HybridDetector,
            RegexDetector,
            SpacyDetector,
        )
        from veildata.pipeline import DetectionPipeline

        if detect_mode == "rules":
            # Rules mode with patterns from config
            vprint(f"Loading RegexDetector with {len(start_patterns)} patterns...")
            detector = RegexDetector(start_patterns)
            return (
                DetectionPipeline(
                    detector, store=store, redaction_format="[{label}_{counter}]"
                ),
                store,
            )

        elif detect_mode in ["ml", "hybrid"]:
            # ML/Hybrid mode
            detectors = []

            # 1. Add ML Detectors
            # Use dot notation from Pydantic model
            spacy_conf = config.ml.spacy
            bert_conf = config.ml.bert

            # If no explicit ML config enabled but mode is ML, enable Spacy default
            if not spacy_conf.enabled and not bert_conf.enabled and detect_mode == "ml":
                spacy_conf.enabled = True

            if spacy_conf.enabled:
                vprint("Loading SpacyDetector...")
                detectors.append(
                    SpacyDetector(
                        model=spacy_conf.model,
                        pii_labels=spacy_conf.pii_labels,
                    )
                )

            if bert_conf.enabled:
                vprint("Loading BertDetector...")
                detectors.append(
                    BertDetector(
                        model_name=bert_conf.model_path,
                        threshold=bert_conf.threshold,
                        label_mapping=bert_conf.label_mapping,
                    )
                )

            # 2. Add Regex Detector for Hybrid mode
            if detect_mode == "hybrid":
                vprint("Loading RegexDetector for Hybrid mode...")
                detectors.append(RegexDetector(start_patterns))

            if not detectors:
                raise ValueError("No detectors enabled for ML/Hybrid mode.")

            if len(detectors) > 1:
                vprint(f"Combining {len(detectors)} detectors in Hybrid mode...")
                hybrid_conf = config.options.hybrid
                detector = HybridDetector(
                    detectors,
                    strategy=hybrid_conf.strategy,
                    prefer=hybrid_conf.prefer,
                )
            else:
                detector = detectors[0]

            return (
                DetectionPipeline(
                    detector, store=store, redaction_format="[{label}_{counter}]"
                ),
                store,
            )

    # Legacy / Rules Mode (no patterns in config) -> Direct Redactor Instantiation
    # Filter config for redactor kwargs
    # We convert model dump to dict and filter irrelevant keys
    redactor_config = config.model_dump(
        exclude={"method", "ml", "traversal", "options", "patterns", "pattern"}
    )

    if method == "all":
        redactors = []
        for key, dotted_path in REDACTOR_REGISTRY.items():
            cls = _lazy_import(dotted_path)
            vprint(f"Loading redactor: {key}")
            redactors.append(cls(store=store, **redactor_config))
        return Compose(redactors), store

    if method not in REDACTOR_REGISTRY:
        raise ValueError(
            f"Unknown redaction method '{method}'. "
            f"Available: {', '.join(list_available_redactors())}"
        )

    cls_path = REDACTOR_REGISTRY[method]
    cls = _lazy_import(cls_path)
    vprint(f"Loading redactor: {method}")

    redactor = cls(store=store, **redactor_config)
    return Compose([redactor]), store


def build_revealer(store_path: str):
    """
    Build a callable revealer from a saved TokenStore mapping.

    Returns:
        callable(text: str) -> str
    """
    store = TokenStore.load(store_path)
    return store.reveal
