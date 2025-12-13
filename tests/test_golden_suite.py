import json
from pathlib import Path

import pytest

from veildata.core.config import VeilConfig
from veildata.engine import build_redactor

# Load GOLDEN_SUITE data
DATA_DIR = Path(__file__).parent / "data"
GOLDEN_SUITE_PATH = DATA_DIR / "golden_suite.json"


def load_test_cases():
    """Load test cases from the golden suite JSON."""
    if not GOLDEN_SUITE_PATH.exists():
        return []
    with open(GOLDEN_SUITE_PATH, "r") as f:
        return json.load(f)


@pytest.mark.parametrize("case", load_test_cases(), ids=lambda c: c["id"])
def test_golden_suite_compliance(case):
    """
    Run each case from the golden suite against the Python SDK.
    """
    # 1. Parse Config
    # We construct VeilConfig directly from the dictionary in the JSON
    config_dict = case["config"]
    # Ensure options structure if missing (default handling)
    if "options" not in config_dict:
        config_dict["options"] = {}

    config = VeilConfig(**config_dict)

    # 2. Build Redactor
    # We use build_redactor but inject our config
    pipeline, _ = build_redactor(config=config, verbose=False)

    # 3. Run Redaction
    # Some older pipelines might be just a callable or an object
    # build_redactor returns (pipeline, store) where pipeline is callable
    result = pipeline(case["input"])

    # 4. Assert
    condition = result == case["expected_redacted"]
    message = f"Failed Case {case['id']}: expected '{case['expected_redacted']}', got '{result}'"

    assert condition, message
