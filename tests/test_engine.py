import pytest

from veildata.engine import load_config
from veildata.exceptions import ConfigMissingError


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
