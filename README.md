# 🕶️ VeilData
**A lightweight framework for masking and unmasking Personally Identifiable Information (PII).**

[![CI](https://github.com/VeilData/veildata/actions/workflows/ci.yml/badge.svg)](https://github.com/VeilData/veildata/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/VeilData/veildata/branch/main/graph/badge.svg)](https://codecov.io/gh/VeilData/veildata)
[![PyPI version](https://img.shields.io/pypi/v/veildata.svg)](https://pypi.org/project/veildata/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/VeilData/veildata/blob/main/LICENSE)

---

### 🧠 Why VeilData

Modern AI systems touch sensitive data every day.  
**VeilData** makes it easy to redact, anonymize, and later restore information.

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
veildata mask input.txt  --method regex --config config.yaml --out masked.txt
```
Example config.yaml
```yaml
patterns:
  EMAIL: "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
```

Reveal previously mask data
```shell
veildata unmask masked.txt --store mappings.json --out revealed.txt
```
** Using Docker**
```shell
docker run --rm -v $(pwd):/app veildata mask input.txt --out masked.txt
```


## Python SDK Examples
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

text = "Apple was founded by Steve Jobs in Cupertino."
masked = masker(text)
print(masked)  # -> [REDACTED_1] was founded by [REDACTED_2] in Cupertino.
```

#### BERT NER Masking
```python
# Requires `pip install veildata[bert]`
from veildata.maskers.ner_bert import BERTNERMasker
from veildata import TokenStore

store = TokenStore()
masker = BERTNERMasker(
    model_name="dslim/bert-base-NER",
    store=store
)

text = "John Smith works at Google in New York."
masked = masker(text)
print(masked)  # -> [REDACTED_1] works at [REDACTED_2] in [REDACTED_3].
```

---

## ⚙️ CLI Configuration

### spaCy PII Detection

```yaml
ml:
  spacy:
    enabled: true
    model: "en_core_web_lg"
    pii_labels:
      - PERSON
      - ORG
      - GPE
      - LOC
      - NORP
```

### BERT-Style PII Detection

```yaml
ml:
  bert:
    enabled: true
    model_path: "models/pii-bert-base"
    threshold: 0.5
    label_mapping:
      EMAIL: ["B-EMAIL", "I-EMAIL"]
      PHONE: ["B-PHONE", "I-PHONE"]
      SSN: ["B-SSN", "I-SSN"]
```

### Hybrid Detection

When using `--detect-mode hybrid`:

1. Run **regex rules** on text → produce spans with types
2. Run **ML/NLP engines** (spaCy + BERT) → produce spans with types + scores
3. Merge spans:
   - If spans overlap with same type → keep the union
   - If spans overlap with different types → configurable resolution

```yaml
options:
  detect_mode: hybrid  # default: rules
  hybrid:
    prefer: ml  # ml | rules | longest_span
```

---

### 🛠️ Continuous Integration
- CI: .github/workflows/ci.yml runs linting, formatting, build, and tests on every push or PR.
- Publish: .github/workflows/publish.yml auto-publishes to PyPI when a new v* tag or release is created.

