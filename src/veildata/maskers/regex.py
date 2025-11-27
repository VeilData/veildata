import re
from typing import Pattern

from veildata.core import Module
from veildata.revealers import TokenStore


class RegexMasker(Module):
    """Mask substrings in text using a regex pattern, optionally tracking reversibility."""

    def __init__(
        self,
        pattern: str,
        mask_token: str = "[REDACTED_{counter}]",
        store: TokenStore | None = None,
    ) -> None:
        super().__init__()
        self.pattern: Pattern[str] = re.compile(pattern)
        self.mask_token = mask_token
        self.store = store
        self.counter = 0

    def forward(self, text: str) -> str:
        def _replace(match):
            self.counter += 1
            token = self.mask_token.format(counter=self.counter)
            if self.store:
                self.store.record(token, match.group(0))
            return token

        return self.pattern.sub(_replace, text)
