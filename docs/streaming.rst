Streaming Redaction
===================

.. module:: veildata.streaming_buffer
   :synopsis: Chunk-based streaming redaction with cross-boundary entity detection

Overview
--------

VeilData supports chunk-based streaming redaction, enabling efficient processing of large files and real-time streams while correctly detecting entities that span across chunk boundaries.

Features
--------

* **Streaming Buffer**: Process text in chunks with minimal memory footprint
* **Cross-Chunk Detection**: Detect entities split across chunk boundaries using sliding window
* **REST API**: FastAPI endpoint for streaming HTTP requests/responses
* **CLI Support**: ``--stream`` flag for processing large files
* **Reversible**: Full TokenStore integration for reveal operations

Quick Start
-----------

Python API
~~~~~~~~~~

.. code-block:: python

   from veildata.detectors import RegexDetector
   from veildata.pipeline import DetectionPipeline
   from veildata.streaming_buffer import StreamingRedactionBuffer

   # Setup
   patterns = {"EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
   detector = RegexDetector(patterns)
   pipeline = DetectionPipeline(detector)
   buffer = StreamingRedactionBuffer(pipeline, overlap_size=512)

   # Process chunks
   for chunk in ["My email is john.do", "e@example.com here"]:
       output = buffer.add_chunk(chunk)
       print(output, end="")

   print(buffer.finalize())
   # Output: My email is [REDACTED_1] here

CLI Streaming
~~~~~~~~~~~~~

.. code-block:: bash

   # Stream large file
   veildata redact large_file.txt --stream --output redacted.txt

   # Custom chunk and overlap sizes
   veildata redact input.txt --stream \
     --chunk-size 8192 \
     --overlap 1024 \
     --output output.txt \
     --store store.json

   # With timing
   veildata redact input.txt --stream --time --verbose

REST API
~~~~~~~~

Start the API server:

.. code-block:: bash

   pip install veildata[api]
   uvicorn veildata.api.app:app --reload

Stream redaction:

.. code-block:: bash

   curl -X POST "http://localhost:8000/v1/redact/stream?overlap_size=256" \
     -H "Content-Type: text/plain" \
     --data-binary @input.txt > output.txt

Get token store:

.. code-block:: bash

   curl -X POST "http://localhost:8000/v1/redact/stream?return_store=true" \
     -H "Content-Type: text/plain" \
     --data-binary @input.txt \
     -v 2>&1 | grep x-token-store

How It Works
------------

Sliding Window Algorithm
~~~~~~~~~~~~~~~~~~~~~~~~~

The streaming buffer uses a sliding window approach:

1. **Buffer Accumulation**: Chunks are appended to an internal buffer
2. **Safe Zone Calculation**: Text before the overlap region is "safe" to output
3. **Cross-Boundary Detection**: Entities in the overlap may span to next chunk
4. **Progressive Output**: Safe text is redacted and yielded immediately
5. **Overlap Retention**: Last N characters are kept for the next iteration

.. code-block:: text

   Chunk 1: "My email is john.do"
            |<---safe--->|<-overlap->|
            "My email is"   "john.do"  <- kept

   Chunk 2: "e@example.com and more"
   Buffer:  "john.doe@example.com and more"
            |<-------safe-------->|<-overlap->|
   Output: "[REDACTED_1] and"      "more"  <- kept

   Finalize: "more"
   Output: "more"

Entity Detection
~~~~~~~~~~~~~~~~

Entities are detected using the full buffer (safe + overlap), but only entities entirely within the safe zone are redacted in the current iteration. This ensures:

* ✅ Entities split across chunks are detected when reassembled
* ✅ No partial entity text is output unredacted
* ✅ Minimal memory usage (only overlap region retained)

Configuration
-------------

Buffer Parameters
~~~~~~~~~~~~~~~~~

**overlap_size** (default: 512)
   Characters to retain between chunks

   * Should be ≥ longest expected entity
   * Larger = better detection, more memory
   * Smaller = less memory, may miss long entities

**chunk_size** (CLI only, default: 4096)
   Bytes to read per chunk

   * Affects I/O performance
   * Does not affect detection accuracy

API Parameters
~~~~~~~~~~~~~~

``POST /v1/redact/stream``

Query parameters:

* ``method``: Redaction method (``regex``, ``ner_spacy``, ``ner_bert``)
* ``detect_mode``: Detection mode (``rules``, ``ml``, ``hybrid``)
* ``overlap_size``: Overlap for cross-chunk detection
* ``chunk_size``: Request body chunk size
* ``return_store``: Include token mappings in response header

Response headers:

* ``X-Redaction-Method``: Method used
* ``X-Overlap-Size``: Overlap size used
* ``X-Token-Store``: JSON token mappings (if requested)

Performance
-----------

Benchmarks
~~~~~~~~~~

Streaming mode provides constant memory usage regardless of file size:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20

   * - File Size
     - Memory (Stream)
     - Memory (Batch)
     - Speedup
   * - 1 MB
     - ~2 MB
     - ~3 MB
     - 1.0x
   * - 10 MB
     - ~2 MB
     - ~15 MB
     - 0.95x
   * - 100 MB
     - ~2 MB
     - ~150 MB
     - 0.9x
   * - 1 GB
     - ~2 MB
     - OOM
     - ∞

.. note::
   Benchmarks with overlap_size=512, chunk_size=4096

When to Use Streaming
~~~~~~~~~~~~~~~~~~~~~

**Use streaming when:**

* ✅ Processing files > 100 MB
* ✅ Real-time stream processing
* ✅ Memory-constrained environments
* ✅ Need progressive output

**Use batch mode when:**

* ✅ Small files (< 10 MB)
* ✅ Maximum performance needed
* ✅ Need explain mode (not supported in streaming)

Limitations
-----------

.. warning::
   * **Explain mode**: Not available in streaming (entities not tracked by position)
   * **Overlap size**: Must be ≥ longest entity for reliable detection
   * **Performance**: ~10% slower than batch for small files due to buffer overhead

Examples
--------

See :doc:`examples` for complete, working examples including:

* Basic buffer usage
* File streaming with progress tracking
* API integration
* CLI usage patterns
* Memory-efficient pipelines

Testing
-------

Run streaming tests:

.. code-block:: bash

   pytest tests/test_streaming_buffer.py -v    # Buffer tests (27 tests)
   pytest tests/test_api.py -v                  # API tests (requires fastapi)

Architecture
------------

Core Components
~~~~~~~~~~~~~~~

:class:`StreamingRedactionBuffer`
   Main buffer with sliding window logic

:class:`ChunkMetadata`
   Tracking for each processed chunk

:func:`stream_redact`
   Convenience wrapper for generators

``app.py``
   FastAPI application with streaming endpoint

Integration Points
~~~~~~~~~~~~~~~~~~

* Compatible with all existing :class:`Detector` implementations
* Uses standard :class:`DetectionPipeline` for processing
* Full :class:`TokenStore` support for reversible redaction
* Drop-in replacement for batch processing in CLI

API Reference
-------------

.. autoclass:: veildata.streaming_buffer.StreamingRedactionBuffer
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: veildata.streaming_buffer.ChunkMetadata
   :members:
   :undoc-members:

.. autofunction:: veildata.streaming_buffer.stream_redact

Future Enhancements
-------------------

* Async streaming buffer for concurrent processing
* Adaptive overlap sizing based on detected entity lengths
* Streaming reveal endpoint
* WebSocket support for real-time streams
* Progress callbacks for large files

.. _streaming-examples:

Examples
--------

See ``examples/streaming_example.py`` for complete working examples.
