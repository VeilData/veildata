.. _universal-config-spec:

VC-63: Universal Configuration Specification
============================================

This document defines the **Universal Redaction Configuration** schema for VeilData.
It is intended to be the single source of truth for the Python SDK, ``veildata`` CLI, and future language implementations (Go, Rust, Node.js).

Format
------

Configuration files can be written in **YAML**, **JSON**, or **TOML**.
By default, tools should look for ``veildata.yaml``, ``veildata.json``, or ``veildata.toml`` in the working directory.

Core Schema
-----------

The configuration structure is flattened to prioritize ease of use.

.. code-block:: yaml

    # 1. Redaction Method (Required)
    # Options: "regex", "ner_spacy", "ner_bert", "hybrid"
    method: "regex"

    # 2. Custom Regex Patterns (Optional)
    # Defines named patterns to be redacted.
    # If method is "regex" or "hybrid", these are active.
    patterns:
      EMAIL: "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
      PHONE: "\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b"
      MY_SECRET: "SECRET-\\d+"

    # 3. Traversal (Optional)
    # Controls how JSON structures are processed.
    traversal:
      policy: "allow"          # "allow" (default) or "deny"
      keys_to_redact:          # Only redaction these keys (if policy=allow)
        - "password"
        - "token"
        - "ssn"
      keys_to_ignore: []       # Never redact these keys
      max_depth: 100

    # 4. Machine Learning (Optional)
    # Settings for AI/ML based detection.
    ml:
      spacy:
        enabled: false
        model: "en_core_web_lg"
        pii_labels: ["PERSON", "ORG", "GPE"]
      bert:
        enabled: false
        model_path: "dslim/bert-base-NER"
        threshold: 0.5

    # 5. Global Options (Optional)
    options:
      fallback: "plaintext"   # "plaintext", "drop", or "error" if redaction fails
      hybrid:
        strategy: "union"     # "union" (redact if either finds it) or "intersection"
        prefer: "ml"

Field Definitions
-----------------

``method``
~~~~~~~~~~

*   **Type**: String
*   **Allowed Values**:
    *   ``regex``: Fast, rule-based matching using ``patterns``.
    *   ``ner_spacy``: Uses spaCy NLP models for entity recognition.
    *   ``ner_bert``: Uses Transformer-based BERT models for high-accuracy NER.
    *   ``hybrid``: Combines ``regex`` and ``ml`` detectors.

``patterns``
~~~~~~~~~~~~

*   **Type**: Dictionary (``key: regex_string``)
*   **Description**: A map of Pattern Name -> Regex String.
*   **Behavior**: When a match is found, it is replaced with ``[<Pattern Name>]`` (e.g., ``[EMAIL]``).

``traversal``
~~~~~~~~~~~~~

Used when the input is detected as structured JSON.

*   ``policy``: If ``allow``, specific keys can be targeted for forced redaction. If ``deny``, specific keys can be protected.
*   ``keys_to_redact``: List of JSON keys whose *values* should always be processed.

``ml``
~~~~~~

Specific settings for the ML engines. These only apply if ``method`` is set to the corresponding engine or ``hybrid``.
