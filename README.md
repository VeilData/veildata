# 🕶️ VeilData
**A lightweight framework for redacting and revealing Personally Identifiable Information (PII).**

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
veildata redact data/input.csv --out data/redacted.csv
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
veildata redact input.txt
```
Example config.yaml
```yaml
patterns:
  EMAIL: "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
```

Reveal previously redact data
```shell
veildata reveal redacted.txt
```
** Using Docker**
```shell
docker run --rm -v $(pwd):/app veildata redact input.txt --out redacted.txt
```

### File Input/Output (CLI)
Redact a file, save the output, and keep a token store for reversibility:
```shell
veildata redact input.txt --output redacted.txt --store store.json
```

Reveal the file using the stored tokens:
```shell
veildata reveal redacted.txt --store store.json
```


## Python SDK Examples
Regex-based Redaction
```python
from veildata import Compose, RegexRedactor, TokenStore

# Create a shared TokenStore for reversible Redaction
store = TokenStore()

# Define your Redaction pipeline with the shared store
redactor = Compose([
    RegexRedactor(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", store=store),  # email
    RegexRedactor(r"\b\d{3}-\d{3}-\d{4}\b", store=store),                           # phone
])

text = "Contact John at john.doe@example.com or call 123-456-7890."

# --- redact the data ---
redacted_text = redactor(text)
print(redacted_text)
# -> Contact John at [REDACTED_1] or call [REDACTED_2].

# --- reveal it later ---
revealed_text = store.reveal(redacted_text)
print(revealed_text)
# -> Contact John at john.doe@example.com or call 123-456-7890.
```

spaCy Named Entity Recognition
```python
# Requires `pip install veildata[spacy]`
from veildata.redactors.ner_spacy import SpacyNERRedactor
from veildata import TokenStore

# Shared token store for reversible revealing
store = TokenStore()

redactor = SpacyNERRedactor(
    entities=["PERSON", "ORG"],
    store=store
)

text = "Apple was founded by Steve Jobs in Cupertino."
redacted = redactor(text)
print(redacted)  # -> [REDACTED_1] was founded by [REDACTED_2] in Cupertino.
```

#### BERT NER Redaction
```python
# Requires `pip install veildata[bert]`
from veildata.redactors.ner_bert import BERTNERRedactor
from veildata import TokenStore

store = TokenStore()
redactor = BERTNERRedactor(
    model_name="dslim/bert-base-NER",
    store=store
)

text = "John Smith works at Google in New York."
redacted = redactor(text)
print(redacted)  # -> [REDACTED_1] works at [REDACTED_2] in [REDACTED_3].
```

#### File Input/Output
```python
from pathlib import Path
from veildata import Compose, RegexRedactor, TokenStore

# Setup redactor
store = TokenStore()
redactor = Compose([
    RegexRedactor(r"\b\d{3}-\d{3}-\d{4}\b", store=store)
])

# Read from file
input_path = Path("input.txt")
if input_path.exists():
    text = input_path.read_text()
    
    # redact
    redacted_text = redactor(text)
    
    # Write to file
    Path("redacted.txt").write_text(redacted_text)
    
    # Save store for later revealing
    store.save("store.json")
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


