# 🕶️ VeilData
**A lightweight, PyTorch-inspired framework for masking and unmasking Personally Identifiable Information (PII).**

[![CI](https://github.com/VeilData/veildata/actions/workflows/ci.yml/badge.svg)](https://github.com/VeilData/veildata/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/veildata.svg)](https://pypi.org/project/veildata/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

### 🧠 Why VeilData

Modern AI systems touch sensitive data every day.  
**VeilData** makes it easy to redact, anonymize, and later restore information—using the same composable design you love from PyTorch.

---

## 🚀 Quick Start

### Installation

**From PyPI**
```bash
pip install veildata
```

**For Development**
```bash
git clone https://github.com/VeilData/veildata.git
cd veildata
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

**Test Your Setup**
```bash
uv run python examples/quickstart.py
```

### Examples
Regex-based Masking
```python
from veildata import Compose, RegexMasker

text = "Contact John Doe at john.doe@gmail.com or call 123-456-7890."
masker = Compose([
    RegexMasker(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    RegexMasker(r"\b\d{3}-\d{3}-\d{4}\b"),                           # phone
])

print(masker(text))
# -> Contact John Doe at [REDACTED] or call [REDACTED].
```

spaCy Named Entity Recognition
```python
from veildata.ner_maskers import SpacyNERMasker

masker = SpacyNERMasker(entities=["PERSON", "ORG", "GPE"])
text = "John works at OpenAI in San Francisco."
print(masker(text))
# -> [REDACTED] works at [REDACTED] in [REDACTED].
```

BERT-based Masking
```python
from veildata.bert_masker import BERTNERMasker

masker = BERTNERMasker(model_name="dslim/bert-base-NER")
text = "Email Jane at jane.doe@example.com"
print(masker(text))
# -> Email [REDACTED] at [REDACTED]
```


### 🛠️ Continuous Integration
- CI: .github/workflows/ci.yml runs linting, formatting, build, and tests on every push or PR.
- Publish: .github/workflows/publish.yml auto-publishes to PyPI when a new v* tag or release is created.