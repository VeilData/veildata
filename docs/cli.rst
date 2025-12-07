Command Line Interface
======================

VeilData provides a comprehensive command-line interface for redacting and revealing sensitive information.

Commands
--------

redact
~~~~~~

Redact sensitive data from files or text.

.. code-block:: bash

   veildata redact [OPTIONS] INPUT

**Arguments:**

* ``INPUT``: Input text or path to file

**Options:**

* ``-o, --output PATH``: Write redacted text to this file
* ``-c, --config PATH``: Path to YAML/JSON config file
* ``-m, --method TEXT``: Redaction engine (regex|ner_spacy|ner_bert|all)
* ``--store PATH``: Path to save reversible TokenStore mapping
* ``-v, --verbose``: Show detailed logs
* ``--dry-run``: Show what would be redacted without replacing text
* ``--explain``: Output detection explanations as JSON
* ``--time``: Show timing information
* ``-s, --stream``: Enable streaming mode for large files
* ``--chunk-size INT``: Chunk size for streaming mode (bytes)
* ``--overlap INT``: Overlap size for cross-chunk detection

**Examples:**

.. code-block:: bash

   # Basic redaction
   veildata redact input.txt -o redacted.txt

   # With token store for reversible redaction
   veildata redact input.txt -o redacted.txt --store store.json

   # Streaming mode for large files
   veildata redact large.txt --stream --chunk-size 8192 --overlap 512

   # Using spaCy NER
   veildata redact input.txt --method ner_spacy -o redacted.txt

   # Dry run to preview redactions
   veildata redact input.txt --dry-run

   # Get explanations
   veildata redact input.txt --explain -o explanations.json

reveal
~~~~~~

Reverse redaction using stored token mappings.

.. code-block:: bash

   veildata reveal [OPTIONS] INPUT

**Arguments:**

* ``INPUT``: Redacted text or path to file

**Options:**

* ``-o, --output PATH``: Write revealed text to this file
* ``--store PATH``: Path to TokenStore mapping file (required)
* ``-v, --verbose``: Show detailed logs

**Examples:**

.. code-block:: bash

   # Reveal redacted file
   veildata reveal redacted.txt --store store.json -o original.txt

   # Reveal from stdin
   echo "[REDACTED_1]" | veildata reveal --store store.json

benchmark
~~~~~~~~~

Run performance benchmarks on different redaction methods.

.. code-block:: bash

   veildata benchmark [OPTIONS]

**Options:**

* ``--methods TEXT``: Comma-separated list of methods to benchmark
* ``--iterations INT``: Number of iterations per method
* ``-o, --output PATH``: Save benchmark results to file

inspect
~~~~~~~

Inspect configuration and available redaction methods.

.. code-block:: bash

   veildata inspect [OPTIONS]

**Options:**

* ``--config PATH``: Config file to inspect
* ``--check-ml``: Check if ML dependencies are installed

version
~~~~~~~

Show VeilData version information.

.. code-block:: bash

   veildata version

doctor
~~~~~~

Check VeilData installation and dependencies.

.. code-block:: bash

   veildata doctor

Configuration Files
-------------------

VeilData supports YAML and JSON configuration files for customizing redaction patterns.

**Example config.yaml:**

.. code-block:: yaml

   patterns:
     EMAIL: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
     PHONE: "\\d{3}-\\d{3}-\\d{4}"
     SSN: "\\d{3}-\\d{2}-\\d{4}"
     CREDIT_CARD: "\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}"

   redaction_format: "<{label}_{counter}>"

**Using configuration:**

.. code-block:: bash

   veildata redact input.txt --config config.yaml -o redacted.txt

Streaming Mode
--------------

For processing large files efficiently, use streaming mode:

.. code-block:: bash

   # Basic streaming
   veildata redact large_file.txt --stream -o redacted.txt

   # Custom chunk and overlap sizes
   veildata redact giant_file.txt --stream \
     --chunk-size 16384 \
     --overlap 1024 \
     -o redacted.txt \
     --store store.json

   # With timing and verbose output
   veildata redact large.txt --stream --time --verbose

**Streaming Parameters:**

* ``--chunk-size``: Number of bytes to read per chunk (default: 4096)
  
  * Larger = fewer I/O operations but more memory
  * Smaller = more I/O but less memory

* ``--overlap``: Characters to retain between chunks (default: 512)
  
  * Should be ≥ longest expected entity
  * Too small = may miss entities at boundaries
  * Too large = more memory usage

See :doc:`streaming` for detailed streaming documentation.
