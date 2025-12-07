Examples
========

This section provides complete, working examples for VeilData streaming functionality.

.. _streaming-examples:

Streaming Examples
------------------

The following examples demonstrate various streaming redaction use cases.

Example 1: Basic Streaming
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows basic chunk-based streaming with cross-chunk entity detection.

.. literalinclude:: ../examples/streaming_example.py
   :language: python
   :pyobject: example_1_basic_streaming
   :linenos:

Example 2: File Streaming
~~~~~~~~~~~~~~~~~~~~~~~~~~

Process a file in chunks and write the redacted output.

.. literalinclude:: ../examples/streaming_example.py
   :language: python
   :pyobject: example_2_file_streaming
   :linenos:

Example 3: API Usage
~~~~~~~~~~~~~~~~~~~~~

Instructions for using the streaming API endpoint.

.. literalinclude:: ../examples/streaming_example.py
   :language: python
   :pyobject: example_3_api_usage
   :linenos:

Example 4: CLI Usage
~~~~~~~~~~~~~~~~~~~~

Command-line examples for streaming mode.

.. literalinclude:: ../examples/streaming_example.py
   :language: python
   :pyobject: example_4_cli_usage
   :linenos:

Complete Example File
---------------------

View the complete example file with all functions:

.. literalinclude:: ../examples/streaming_example.py
   :language: python
   :linenos:
   :caption: examples/streaming_example.py

Running the Examples
--------------------

To run the complete example:

.. code-block:: bash

   cd examples
   python streaming_example.py

This will:

1. Demonstrate basic buffer usage with console output
2. Create test files (``test_input.txt``, ``test_output.txt``)
3. Show token store mappings
4. Display API and CLI usage instructions

Additional Examples
-------------------

Integration with Custom Detectors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from veildata.detectors import RegexDetector, SpacyDetector
   from veildata.pipeline import DetectionPipeline
   from veildata.streaming_buffer import stream_redact

   # Combine multiple detectors
   patterns = {
       "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
       "PHONE": r"\d{3}-\d{3}-\d{4}",
   }
   regex_detector = RegexDetector(patterns)
   pipeline = DetectionPipeline(regex_detector)

   # Stream from generator
   def chunk_generator(filepath):
       with open(filepath, 'r') as f:
           while True:
               chunk = f.read(4096)
               if not chunk:
                   break
               yield chunk

   # Process stream
   for output in stream_redact(chunk_generator("input.txt"), pipeline):
       print(output, end="")

Progress Tracking
~~~~~~~~~~~~~~~~~

Track progress while streaming large files:

.. code-block:: python

   from veildata.streaming_buffer import StreamingRedactionBuffer
   from veildata.engine import build_redactor

   redactor, store = build_redactor(method="regex")
   buffer = StreamingRedactionBuffer(redactor, overlap_size=512)

   file_size = os.path.getsize("large_file.txt")
   processed = 0

   with open("large_file.txt") as f:
       while chunk := f.read(4096):
           processed += len(chunk)
           output = buffer.add_chunk(chunk)
           
           # Show progress
           percent = (processed / file_size) * 100
           print(f"\rProgress: {percent:.1f}%", end="", flush=True)
           
           # Write output
           # ... handle output ...

   final = buffer.finalize()
   print(f"\n✓ Complete! {buffer.get_stats()['total_entities_redacted']} entities redacted")

Memory-Efficient Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~

For extremely large files, write directly to output without accumulating:

.. code-block:: python

   from veildata.streaming_buffer import StreamingRedactionBuffer
   from veildata.engine import build_redactor

   redactor, store = build_redactor(method="regex")
   buffer = StreamingRedactionBuffer(redactor, overlap_size=512)

   with open("input.txt") as infile, open("output.txt", "w") as outfile:
       while chunk := infile.read(8192):  # 8KB chunks
           redacted = buffer.add_chunk(chunk)
           if redacted:
               outfile.write(redacted)
       
       # Don't forget the final chunk
       final = buffer.finalize()
       if final:
           outfile.write(final)

   # Save store for reversibility
   store.save("store.json")

See Also
--------

* :doc:`streaming` - Detailed streaming documentation
* :doc:`api` - API reference
* :doc:`cli` - Command-line usage
