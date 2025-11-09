import re

from src.veildata.core import Module


class RegexMasker(Module):
    def __init__(self, pattern, mask_token="[REDACTED]"):
        super().__init__()
        self.pattern = re.compile(pattern)
        self.mask_token = mask_token

    def forward(self, text):
        return self.pattern.sub(self.mask_token, text)
