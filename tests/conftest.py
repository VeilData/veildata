import subprocess

import pytest


@pytest.fixture(scope="session")
def cli_exists():
    result = subprocess.run(
        ["uv", "run", "veildata", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0, "veildata CLI not found"
