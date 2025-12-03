from typing import Any, Callable, List


class Compose:
    """
    Compose multiple redaction components (RegexRedactor, SpacyRedactor, etc.)
    into a single callable pipeline.
    """

    def __init__(self, modules: List[Callable[..., Any]]):
        self.modules = modules

    def __call__(self, text: str, **kwargs) -> str:
        """Run all modules sequentially on the input text."""
        for module in self.modules:
            text = module(text, **kwargs)
        return text

    def __repr__(self):
        names = [m.__class__.__name__ for m in self.modules]
        return f"Compose({', '.join(names)})"
