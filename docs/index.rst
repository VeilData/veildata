VeilData Documentation
======================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   examples
   streaming
   api
   cli

VeilData is a powerful PII redaction library that supports multiple detection methods and streaming processing for large files.

Features
--------

* **Multiple Detection Methods**: Regex, spaCy NER, BERT NER, and hybrid approaches
* **Streaming Support**: Process large files efficiently with chunk-based streaming
* **Reversible Redaction**: TokenStore for mapping redacted tokens back to originals
* **CLI & API**: Command-line interface and REST API endpoints
* **Cross-Chunk Detection**: Detect entities spanning chunk boundaries

Installation
------------

.. code-block:: bash

   # Basic installation
   pip install veildata

   # With spaCy support
   pip install veildata[spacy]

   # With BERT support
   pip install veildata[bert]

   # With API support
   pip install veildata[api]

   # Everything
   pip install veildata[all]

Quick Example
-------------

.. code-block:: python

   from veildata.engine import build_redactor

   # Build a redactor
   redactor, store = build_redactor(method="regex")

   # Redact text
   text = "Contact me at john@example.com or call 555-1234"
   redacted = redactor(text)
   print(redacted)
   # Output: Contact me at [REDACTED_1] or call [REDACTED_2]

   # Reveal original
   revealed = store.reveal(redacted)
   print(revealed)
   # Output: Contact me at john@example.com or call 555-1234

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
