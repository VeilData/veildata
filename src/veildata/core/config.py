import json
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from veildata.exceptions import ConfigMissingError

# --- Enums ---


class RedactionMethod(str, Enum):
    REGEX = "regex"
    NER_SPACY = "ner_spacy"
    NER_BERT = "ner_bert"
    HYBRID = "hybrid"


class TraversalPolicy(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


# --- Configuration Models ---


class SpacyConfig(BaseModel):
    enabled: bool = False
    model: str = "en_core_web_lg"
    pii_labels: Optional[List[str]] = None


class BertConfig(BaseModel):
    enabled: bool = False
    model_path: str = "dslim/bert-base-NER"
    threshold: float = 0.5
    label_mapping: Optional[Dict[str, str]] = None


class MLConfig(BaseModel):
    spacy: SpacyConfig = Field(default_factory=SpacyConfig)
    bert: BertConfig = Field(default_factory=BertConfig)


class TraversalConfig(BaseModel):
    """Configuration for JSON traversal."""

    policy: TraversalPolicy = TraversalPolicy.ALLOW
    keys_to_redact: List[str] = Field(default_factory=list)
    keys_to_ignore: List[str] = Field(default_factory=list)
    max_depth: int = 100


class HybridOptions(BaseModel):
    strategy: str = "union"
    prefer: str = "ml"


class GlobalOptions(BaseModel):
    hybrid: HybridOptions = Field(default_factory=HybridOptions)
    fallback: str = "plaintext"


class VeilConfig(BaseModel):
    """Root configuration for VeilData."""

    method: RedactionMethod = RedactionMethod.REGEX

    # Redaction Rules
    patterns: Optional[Dict[str, str]] = None
    # Alias for legacy config support
    pattern: Optional[Dict[str, str]] = None

    # ML settings
    ml: MLConfig = Field(default_factory=MLConfig)

    # Traversal settings
    traversal: TraversalConfig = Field(default_factory=TraversalConfig)

    # Global options
    options: GlobalOptions = Field(default_factory=GlobalOptions)

    def get_patterns(self) -> Dict[str, str]:
        """Helper to get patterns from either 'patterns' or 'pattern' field."""
        return self.patterns or self.pattern or {}


# --- Loading Logic ---


def load_config(config_path: Optional[str] = None, verbose: bool = False) -> VeilConfig:
    """
    Load configuration from a file or environment variables.

    Args:
        config_path: Path to the config file (YAML, JSON, TOML).
        verbose: Whether to print loading status.

    Returns:
        VeilConfig object.

    Raises:
        ConfigMissingError: If specified config file is not found.
        ValidationError: If config is invalid.
    """
    config_dict = {}

    # 1. Resolve Path
    if not config_path:
        default_path = Path.home() / ".veildata" / "config.toml"
        # Also check local directory for config.yaml/json/toml
        local_defaults = ["veildata.yaml", "veildata.json", "veildata.toml"]

        for local in local_defaults:
            if Path(local).exists():
                config_path = local
                break

        if not config_path and default_path.exists():
            config_path = str(default_path)

    # 2. Load File
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise ConfigMissingError(f"Configuration file not found: {config_path}")

        try:
            text = path.read_text(encoding="utf-8")
            if verbose:
                print(f"[veildata] Loaded config from {path.absolute()}")

            if config_path.endswith(".json"):
                config_dict = json.loads(text)
            elif config_path.endswith(".toml"):
                config_dict = tomllib.loads(text)
            else:  # YAML is default
                config_dict = yaml.safe_load(text) or {}

        except Exception as e:
            # Re-raise as ValidationError if it's a parsing issue, or general error
            if verbose:
                print(f"[veildata] Error loading config: {e}")
            raise e

    # 3. Environment Variable Overrides (Minimal example)
    # VEILDATA_METHOD=ner_spacy override
    env_method = os.getenv("VEILDATA_METHOD")
    if env_method:
        config_dict["method"] = env_method

    # 4. Validate and Return
    try:
        return VeilConfig(**config_dict)
    except ValidationError as e:
        if verbose:
            print(f"[veildata] Configuration validation error: {e}")
        raise e
