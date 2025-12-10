from unittest.mock import patch

from veildata.core.config import RedactionMethod, VeilConfig
from veildata.engine import load_config


def test_load_config_toml(tmp_path):
    """Test loading a TOML config file."""
    config_file = tmp_path / "config.toml"
    # Use valid fields for GlobalOptions
    config_file.write_text('method = "regex"\n[options]\nfallback = "plaintext"')

    config = load_config(str(config_file))

    assert config.method == RedactionMethod.REGEX
    assert config.options.fallback == "plaintext"


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
    # "default" is not a valid enum member for RedactionMethod based on config.py enum definition
    # Assuming the user meant "regex" as it is the default, or if "default" was a string in legacy.
    # Looking at config.py: RedactionMethod.REGEX = "regex".
    # Let's use valid enum value "regex" to be safe, or check if "default" is supported.
    # The previous code had 'method = "default"', likely legacy.
    # Let's switch to 'regex' to pass validation.
    config_file.write_text('method = "regex"')

    config = load_config(None)

    assert config.method == RedactionMethod.REGEX


@patch("pathlib.Path.home")
def test_load_config_no_default(mock_home, tmp_path):
    """Test loading when no default config exists."""
    mock_home.return_value = tmp_path
    # No file created

    config = load_config(None)
    # load_config returns a default VeilConfig object, not an empty dict
    assert isinstance(config, VeilConfig)
    assert config.method == RedactionMethod.REGEX
