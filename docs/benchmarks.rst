
Performance Study: Streaming & Traversal Analysis
=================================================

This study evaluates the performance characteristics of Veildata's new capabilities: **Streaming Redaction (VC-50)** and **Structure-Aware JSON Traversal (VC-51)**.

1. Study Motivation
-------------------
As Veildata evolves to handle enterprise-scale workloads, we must understand the performance trade-offs introduced by advanced features.
- **Streaming**: Enables processing infinite-size files but introduces buffer management overhead.
- **Traversal**: Ensures structural integrity of JSON/Objects but requires recursive processing.

The goal of this study is to quantify this overhead to inform users when to use which method.

2. Hypothesis
-------------
Before execution, we hypothesized:
- **Streaming vs. Baseline**: Streaming should have a **constant factor overhead** (1.5x - 2.0x) due to the need to manage overlapping buffers and stitch chunk outputs. Memory usage should remain constant regardless of input size.
- **Traversal vs. Baseline**: Recursive traversal should be significantly slower (**2x - 4x**) than flat string processing due to the overhead of Python object inspection and reconstruction.

3. Methodology
--------------
- **Environment**: WSL (Ubuntu 22.04) running on Windows, Python 3.12.3.
- **Dataset**: 1MB generated payloads with high PII density.
    - *Text*: Mixed prose and structured identifiers.
    - *JSON*: Deeply nested (depth=5) objects.
- **Metric**: End-to-end latency (seconds), averaged over multiple runs using ``timeit``.

4. Observations
---------------

.. note::
    Results gathered on 2025-12-07. Lower latency is better.

.. list-table:: Benchmark Results
   :widths: 20 40 20 20
   :header-rows: 1

   * - Test ID
     - Method
     - Latency (s)
     - Multiplier
   * - Baseline-A
     - Non-Streaming (Naive)
     - 0.038s
     - 1.0x (Ref)
   * - Test-A (VC-50)
     - Streaming Redaction
     - 0.066s
     - 1.73x
   * - Baseline-B
     - Flat JSON (as String)
     - 0.080s
     - 1.0x (Ref)
   * - Test-B (VC-51)
     - Nested JSON Traversal
     - 0.223s
     - 2.78x

5. Deep Dive Analysis
---------------------

Why is Streaming Slower? (1.73x Overhead)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The observed ~73% increase in latency is driven by three specific factors identified in ``streaming_buffer.py``:

1.  **Overlap Redundancy (Double Processing)**:
    To detect entities split across chunks (e.g., an email cut in half), the buffer retains trailing bytes (default 512). This means ~12% of data (with 4KB chunks) is processed by the regex engine **twice**.

2.  **String Manipulation Costs**:
    Unlike the baseline which processes one large string, streaming requires:
    - *Concatenation* (``buffer += chunk``)
    - *Slicing* (``buffer = buffer[safe_end:]``)
    - *Joining* result lists.
    These operations occur 256 times for a 1MB file (4KB chunks).

3.  **Per-Chunk Logic**:
    Fixed costs such as sorting detected spans and calculating "safe zones" are paid per-chunk rather than once-per-file.

**Conclusion**: This overhead is the "cost of stability." It buys the ability to process 10GB files with constant RAM usage.

Why is Traversal Slower? (2.78x Overhead)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ~178% latency increase for JSON traversal is due to the shift from **O(N)** string scanning to **O(N) + O(Nodes)** object manipulation:

1.  **Object Overhead**: Iterating through dictionary keys and list items in Python is roughly 10-20x slower than a C-optimized regex scan over raw bytes.
2.  **Reconstruction**: The traversal function creates a *new* copy of the data structure (to avoid mutating the original), essentially performing a deep copy with modifications.
3.  **Callback Overhead**: The redactor is called as a function for every leaf node string, incurring Python function call overheads compared to a single bulk ``re.sub``.

**Conclusion**: Use structure-aware traversal *only* when you must preserve the JSON schema (e.g., sending data to an API). For logs or dump files where structure is less critical, raw string processing is faster.
