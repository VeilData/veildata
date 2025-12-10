import os

import pytest
from pydantic import ValidationError

from veildata.core.config import (
    RedactionMethod,
    TraversalPolicy,
    VeilConfig,
    load_config,
)
from veildata.exceptions import ConfigMissingError

# --- Fixtures ---


@pytest.fixture
def clean_env():
    """Ensure environment is clean before/after tests."""
    old_method = os.environ.get("VEILDATA_METHOD")
    if old_method:
        del os.environ["VEILDATA_METHOD"]
    yield
    if old_method:
        os.environ["VEILDATA_METHOD"] = old_method
    elif "VEILDATA_METHOD" in os.environ:
        del os.environ["VEILDATA_METHOD"]


@pytest.fixture
def config_file(tmp_path):
    """Helper to create a temp config file."""

    def _create(content: str, ext: str = "yaml"):
        f = tmp_path / f"config.{ext}"
        f.write_text(content, encoding="utf-8")
        return str(f)

    return _create


# --- Tests ---


def test_load_config_defaults():
    """Test loading default configuration values."""
    config = VeilConfig()
    assert config.method == RedactionMethod.REGEX
    assert config.ml.spacy.enabled is False
    assert config.traversal.policy == TraversalPolicy.ALLOW


def test_load_config_from_yaml(config_file):
    """Test loading valid YAML config."""
    yaml_content = """
    method: ner_spacy
    ml:
      spacy:
        enabled: true
        model: en_core_web_sm
    traversal:
      policy: deny
      keys_to_redact: ["password", "secret"]
    """
    path = config_file(yaml_content, "yaml")
    config = load_config(path)

    assert config.method == RedactionMethod.NER_SPACY
    assert config.ml.spacy.enabled is True
    assert config.ml.spacy.model == "en_core_web_sm"
    assert config.traversal.policy == TraversalPolicy.DENY
    assert "password" in config.traversal.keys_to_redact


def test_load_config_from_json(config_file):
    """Test loading valid JSON config."""
    json_content = """
    {
        "method": "hybrid",
        "patterns": {
            "TEST": "\\\\d+"
        }
    }
    """
    path = config_file(json_content, "json")
    config = load_config(path)

    assert config.method == RedactionMethod.HYBRID
    assert "TEST" in config.patterns


def test_load_config_missing_file():
    """Test error raised when config file missing."""
    with pytest.raises(ConfigMissingError):
        load_config("/non/existent/path/config.yaml")


def test_load_config_env_override(config_file, clean_env):
    """Test environment variables override file config."""
    yaml_content = "method: regex"
    path = config_file(yaml_content)

    os.environ["VEILDATA_METHOD"] = "ner_bert"
    config = load_config(path)

    assert config.method == RedactionMethod.NER_BERT


def test_validation_error(config_file):
    """Test invalid config raises ValidationError."""
    # 'invalid_method' is not a valid RedactionMethod
    yaml_content = "method: invalid_method"
    path = config_file(yaml_content)

    with pytest.raises(ValidationError) as excinfo:
        load_config(path)
    assert "Input should be 'regex', 'ner_spacy', 'ner_bert' or 'hybrid'" in str(
        excinfo.value
    )


def test_pattern_alias(config_file):
    """Test that 'pattern' alias works for 'patterns'."""
    yaml_content = """
    pattern:
      SSN: "\\\\d{3}-\\\\d{2}-\\\\d{4}"
    """
    path = config_file(yaml_content)
    config = load_config(path)

    assert config.patterns is None
    assert config.pattern is not None
    assert "SSN" in config.get_patterns()


def test_traversal_config_defaults():
    """Test traversal defaults are safe."""
    config = VeilConfig()
    assert config.traversal.max_depth == 100
    assert config.traversal.keys_to_redact == []
