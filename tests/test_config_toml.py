from unittest.mock import patch

from veildata.engine import load_config


def test_load_config_toml(tmp_path):
    """Test loading a TOML config file."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('method = "regex"\n[options]\nfoo = "bar"')

    config = load_config(str(config_file))

    assert config["method"] == "regex"
    assert config["options"]["foo"] == "bar"


@patch("pathlib.Path.home")
def test_load_config_default(mock_home, tmp_path):
    """Test loading default config when path is None."""
    # Setup mock home directory
    mock_home.return_value = tmp_path

    # Create default config
    veildata_dir = tmp_path / ".veildata"
    veildata_dir.mkdir()
    config_file = veildata_dir / "config.toml"
    config_file.write_text('method = "default"')

    # Load with None
    config = load_config(None)

    assert config["method"] == "default"


@patch("pathlib.Path.home")
def test_load_config_no_default(mock_home, tmp_path):
    """Test loading when no default config exists."""
    mock_home.return_value = tmp_path
    # No file created

    config = load_config(None)
    assert config == {}
