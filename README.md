# 🕶️ VeilData
**A lightweight framework for masking and unmasking Personally Identifiable Information (PII).**

[![CI](https://github.com/VeilData/veildata/actions/workflows/ci.yml/badge.svg)](https://github.com/VeilData/veildata/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/VeilData/veildata/branch/main/graph/badge.svg)](https://codecov.io/gh/VeilData/veildata)
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
```shell
pip install veildata
```
**Run from Docker**
```shell
docker build -t veildata .
alias veildata="docker run --rm -v \$(pwd):/app veildata"
veildata mask data/input.csv --out data/redacted.csv
```

**Running in Docker**
```shell
docker build -t veildata .
docker run -it ghcr.io/veildata/veildata:latest
```

**For Development**
```shell
git clone https://github.com/VeilData/veildata.git
cd veildata
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
uv sync
```

### Quickstart Guide
Mark sensitive data
```shell
veildata mask input.txt --out masked.txt
```
Reveal previously mask data
```shell
veildata unmask masked.txt --store mappings.json --out revealed.txt
```
** Using Docker**
```shell
docker run --rm -v $(pwd):/app veildata mask input.txt --out masked.txt
```


### Examples
Regex-based Masking
```python
from veildata import Compose, RegexMasker, TokenStore

# Create a shared TokenStore for reversible masking
store = TokenStore()

# Define your masking pipeline with the shared store
masker = Compose([
    RegexMasker(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", store=store),  # email
    RegexMasker(r"\b\d{3}-\d{3}-\d{4}\b", store=store),                           # phone
])

text = "Contact John at john.doe@example.com or call 123-456-7890."

# --- Mask the data ---
masked_text = masker(text)
print(masked_text)
# -> Contact John at [REDACTED_1] or call [REDACTED_2].

# --- Unmask it later ---
unmasked_text = store.unmask(masked_text)
print(unmasked_text)
# -> Contact John at john.doe@example.com or call 123-456-7890.
```

spaCy Named Entity Recognition
```python
# Requires `pip install veildata[spacy]`
from veildata.maskers.ner_spacy import SpacyNERMasker
from veildata import TokenStore

# Shared token store for reversible unmasking
store = TokenStore()

masker = SpacyNERMasker(
    entities=["PERSON", "ORG"],
    store=store
)

text = "John works at OpenAI in San Francisco."

# --- Mask automatically and track mappings ---
masked = masker(text)
print(masked)
# -> [REDACTED_1] works at [REDACTED_2] in San Francisco.

# --- Unmask using the same store ---
unmasked = store.unmask(masked)
print(unmasked)
# -> John works at OpenAI in San Francisco.
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
