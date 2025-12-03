import re
from typing import Pattern

from veildata.core import Module
from veildata.revealers import TokenStore


class RegexRedactor(Module):
    """Redact substrings in text using a regex pattern, optionally tracking reversibility."""

    def __init__(
        self,
        pattern: str,
        redaction_token: str = "[REDACTED_{counter}]",
        store: TokenStore | None = None,
    ) -> None:
        super().__init__()
        self.pattern: Pattern[str] = re.compile(pattern)
        self.redaction_token = redaction_token
        self.store = store
        self.counter = 0

    def forward(self, text: str) -> str:
        def _replace(match):
            self.counter += 1
            token = self.redaction_token.format(counter=self.counter)
            if self.store:
                self.store.record(token, match.group(0))
            return token

        return self.pattern.sub(_replace, text)
