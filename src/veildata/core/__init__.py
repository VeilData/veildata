from typing import Any


class Module:
    """Base component class for all VeilData transformers."""

    def __init__(self) -> None:
        self.training = True

    def train(self, mode: bool = True) -> "Module":
        """Set the module to training or eval mode."""
        self.training = mode
        return self

    def eval(self) -> "Module":
        """Shortcut for setting eval mode."""
        return self.train(False)

    def forward(self, x: Any) -> Any:
        """Override this method with the transformation logic."""
        raise NotImplementedError("forward() not implemented")

    def __call__(self, x: Any) -> Any:
        return self.forward(x)
