# Default regex patterns for one-shot masking
DEFAULT_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "IPV4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
}
