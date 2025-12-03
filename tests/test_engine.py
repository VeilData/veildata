from unittest.mock import patch

import pytest

from veildata.engine import (
    build_redactor,
    build_revealer,
    list_available_redactors,
    list_engines,
    load_config,
)
from veildata.exceptions import ConfigMissingError
from veildata.revealers import TokenStore


def test_load_config_missing_file():
    """Test that load_config raises ConfigMissingError when file does not exist."""
    with pytest.raises(ConfigMissingError):
        load_config("non_existent_config.yaml")


def test_load_config_valid_file(tmp_path):
    """Test that load_config loads a valid config file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("key: value")

    config = load_config(str(config_file))
    assert config == {"key": "value"}


def test_list_engines():
    engines = list_engines()
    assert len(engines) > 0
    names = [e[0] for e in engines]
    assert "regex" in names
    assert "spacy" in names
    assert "hybrid" in names


def test_list_available_redactors():
    redactors = list_available_redactors()
    assert "regex" in redactors
    assert "ner_spacy" in redactors
    assert "all" in redactors


def test_build_redactor_regex():
    config = {"patterns": {"TEST": "test"}}
    redactor, store = build_redactor(method="regex", config_dict=config)
    assert hasattr(redactor, "detector")  # Should be a pipeline
    assert store is not None


@patch("veildata.engine.load_config")
@patch("veildata.detectors.SpacyDetector")
def test_build_redactor_spacy_ml(mock_spacy, mock_load_config):
    config = {"patterns": {"dummy": "pattern"}}
    # load_config is called for ml_config. Return spacy config.
    mock_load_config.return_value = {"ml": {"spacy": {"enabled": True}}}

    redactor, store = build_redactor(
        method="ner_spacy", detect_mode="ml", config_dict=config
    )
    assert hasattr(redactor, "detector")
    mock_spacy.assert_called()


@patch("veildata.engine.load_config")
@patch("veildata.detectors.BertDetector")
def test_build_redactor_bert_ml(mock_bert, mock_load_config):
    config = {"patterns": {"dummy": "pattern"}}
    # load_config is called for ml_config. Return bert config.
    mock_load_config.return_value = {"ml": {"bert": {"enabled": True}}}

    redactor, store = build_redactor(
        method="ner_bert", detect_mode="ml", config_dict=config
    )
    assert hasattr(redactor, "detector")
    mock_bert.assert_called()


def test_build_revealer(tmp_path):
    store = TokenStore()
    store.record("[REDACTED_1]", "secret")
    store_path = tmp_path / "tokens.json"
    store.save(str(store_path))

    revealer = build_revealer(str(store_path))
    assert revealer("This is [REDACTED_1]") == "This is secret"
