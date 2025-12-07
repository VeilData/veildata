Quick Start
===========

This guide will help you get started with VeilData.

Installation
------------

Install VeilData using pip:

.. code-block:: bash

   pip install veildata

For additional features, install optional dependencies:

.. code-block:: bash

   pip install veildata[api]     # REST API support
   pip install veildata[spacy]   # spaCy NER support
   pip install veildata[bert]    # BERT NER support
   pip install veildata[all]     # All features

Basic Usage
-----------

Python API
~~~~~~~~~~

.. code-block:: python

   from veildata.engine import build_redactor

   # Build a redactor
   redactor, store = build_redactor(method="regex")

   # Redact text
   text = "My email is john@example.com and phone is 555-1234"
   redacted = redactor(text)
   print(redacted)
   # Output: My email is [REDACTED_1] and phone is [REDACTED_2]

   # Reveal original (reversible redaction)
   revealed = store.reveal(redacted)
   assert revealed == text

Command Line
~~~~~~~~~~~~

.. code-block:: bash

   # Redact a file
   veildata redact input.txt --output redacted.txt --store store.json

   # Reveal redacted text
   veildata reveal redacted.txt --store store.json --output original.txt

   # Use different detection methods
   veildata redact input.txt --method ner_spacy --output redacted.txt

Streaming Large Files
~~~~~~~~~~~~~~~~~~~~~

For large files, use streaming mode:

.. code-block:: bash

   veildata redact large_file.txt --stream --output redacted.txt

.. code-block:: python

   from veildata.streaming_buffer import StreamingRedactionBuffer
   from veildata.engine import build_redactor

   redactor, store = build_redactor(method="regex")
   buffer = StreamingRedactionBuffer(redactor, overlap_size=512)

   # Process file in chunks
   with open("large_file.txt") as f:
       while chunk := f.read(4096):
           output = buffer.add_chunk(chunk)
           print(output, end="")
   print(buffer.finalize())

Next Steps
----------

* Learn about :doc:`streaming` for efficient large file processing
* Explore the :doc:`api` reference
* Check out :doc:`cli` for command-line usage
