from typing import Any, Callable, List


class Compose:
    """
    Compose multiple masking components (RegexMasker, SpacyMasker, etc.)
    into a single callable pipeline.
    """

    def __init__(self, maskers: List[Callable[..., Any]]):
        self.maskers = maskers

    def __call__(self, text: str, **kwargs) -> str:
        """Run all maskers sequentially on the input text."""
        for masker in self.maskers:
            text = masker(text, **kwargs)
        return text

    def __repr__(self):
        names = [m.__class__.__name__ for m in self.maskers]
        return f"Compose({', '.join(names)})"
