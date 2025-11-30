from unittest.mock import patch

import pytest

from veildata.engine import (
    build_masker,
    build_unmasker,
    list_available_maskers,
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


def test_list_available_maskers():
    maskers = list_available_maskers()
    assert "regex" in maskers
    assert "ner_spacy" in maskers
    assert "all" in maskers


def test_build_masker_regex():
    config = {"patterns": {"TEST": "test"}}
    masker, store = build_masker(method="regex", config_dict=config)
    assert hasattr(masker, "detector")  # Should be a pipeline
    assert store is not None


@patch("veildata.engine.load_config")
@patch("veildata.detectors.SpacyDetector")
def test_build_masker_spacy_ml(mock_spacy, mock_load_config):
    config = {"patterns": {"dummy": "pattern"}}
    # load_config is called for ml_config. Return spacy config.
    mock_load_config.return_value = {"ml": {"spacy": {"enabled": True}}}

    masker, store = build_masker(
        method="ner_spacy", detect_mode="ml", config_dict=config
    )
    assert hasattr(masker, "detector")
    mock_spacy.assert_called()


@patch("veildata.engine.load_config")
@patch("veildata.detectors.BertDetector")
def test_build_masker_bert_ml(mock_bert, mock_load_config):
    config = {"patterns": {"dummy": "pattern"}}
    # load_config is called for ml_config. Return bert config.
    mock_load_config.return_value = {"ml": {"bert": {"enabled": True}}}

    masker, store = build_masker(
        method="ner_bert", detect_mode="ml", config_dict=config
    )
    assert hasattr(masker, "detector")
    mock_bert.assert_called()


def test_build_unmasker(tmp_path):
    store = TokenStore()
    store.record("[REDACTED_1]", "secret")
    store_path = tmp_path / "tokens.json"
    store.save(str(store_path))

    unmasker = build_unmasker(str(store_path))
    assert unmasker("This is [REDACTED_1]") == "This is secret"
