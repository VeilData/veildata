from typing import Any, Callable


def traverse_and_redact(data: Any, redactor_func: Callable[[str], str]) -> Any:
    """
    Recursively traverse a JSON-like structure (dict, list, primitive) and apply
    redactor_func to all string values.

    Args:
        data: The input data (dict, list, str, int, etc.).
        redactor_func: A function that takes a string and returns a redacted string.

    Returns:
        The structure with strings redacted, preserving original structure and types.
    """
    if isinstance(data, dict):
        return {k: traverse_and_redact(v, redactor_func) for k, v in data.items()}
    elif isinstance(data, list):
        return [traverse_and_redact(item, redactor_func) for item in data]
    elif isinstance(data, str):
        return redactor_func(data)
    else:
        # Preserve int, float, bool, None, etc.
        return data
