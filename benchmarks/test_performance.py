import timeit

import pytest

from veildata.detectors import RegexDetector
from veildata.pipeline import DetectionPipeline
from veildata.streaming_buffer import stream_redact
from veildata.utils.traversal import traverse_and_redact

from .utils import (
    generate_chunk_stream,
    generate_flat_json,
    generate_large_text,
    generate_nested_json,
)

# Global results storage
RESULTS = []


@pytest.fixture(scope="module")
def benchmark_data():
    """Generates data once for all tests."""
    print("\n\nGenerating benchmark data... (this may take a moment)")
    plain_text = generate_large_text(size_mb=1.0)
    flat_json_str = generate_flat_json(
        size_mb=1.0
    )  # String representation of flat JSON
    nested_json_obj = generate_nested_json(depth=5, size_mb=1.0)  # Dict object

    # Pre-warm detectors to avoid initialization cost in benchmark
    detector = RegexDetector(
        {
            "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "PHONE": r"\d{3}-\d{3}-\d{4}",
        }
    )
    pipeline = DetectionPipeline(detector)

    return {
        "plain_text": plain_text,
        "flat_json_str": flat_json_str,
        "nested_json_obj": nested_json_obj,
        "pipeline": pipeline,
    }


@pytest.fixture(scope="module", autouse=True)
def print_summary():
    """Prints the summary table after all tests in this module finish."""
    yield
    print("\n" + "=" * 80)
    print(f"{'Test ID':<20} | {'Method':<25} | {'Latency (s)':<15}")
    print("-" * 80)
    for res in RESULTS:
        print(f"{res['id']:<20} | {res['method']:<25} | {res['time']:.5f}")
    print("=" * 80 + "\n")


def record_result(test_id, method_name, elapsed_time):
    RESULTS.append({"id": test_id, "method": method_name, "time": elapsed_time})


def test_baseline_a_plain_text(benchmark_data):
    """Test ID: Baseline-A (Old Non-Streaming)"""
    pipeline = benchmark_data["pipeline"]
    text = benchmark_data["plain_text"]

    start_time = timeit.default_timer()
    _ = pipeline.forward(text)
    elapsed = timeit.default_timer() - start_time

    record_result("Baseline-A", "Non-Streaming (Naive)", elapsed)


def test_streaming_a_chunks(benchmark_data):
    """Test ID: Test-A (VC-50: New Streaming)"""
    pipeline = benchmark_data["pipeline"]
    text = benchmark_data["plain_text"]

    # Generator creation is fast, but we include it or exclude it?
    # Usually we benchmark the consumption.
    chunk_gen = generate_chunk_stream(text, chunk_size=4096)

    start_time = timeit.default_timer()
    # Consume the generator to ensure processing happens
    _ = list(stream_redact(chunk_gen, pipeline))
    elapsed = timeit.default_timer() - start_time

    record_result("Test-A (VC-50)", "Streaming Redaction", elapsed)


def test_baseline_b_flat_json(benchmark_data):
    """Test ID: Baseline-B (Old Non-JSON)"""
    pipeline = benchmark_data["pipeline"]
    json_str = benchmark_data["flat_json_str"]

    start_time = timeit.default_timer()
    # Naive approach: treat JSON string as plain text
    _ = pipeline.forward(json_str)
    elapsed = timeit.default_timer() - start_time

    record_result("Baseline-B", "Flat JSON (as String)", elapsed)


def test_traversal_b_nested_json(benchmark_data):
    """Test ID: Test-B (VC-51: New JSON Traversal)"""
    pipeline = benchmark_data["pipeline"]
    data_obj = benchmark_data["nested_json_obj"]

    # Helper to function as the redactor callback
    def redactor_func(text_val):
        return pipeline.forward(text_val)

    start_time = timeit.default_timer()
    _ = traverse_and_redact(data_obj, redactor_func)
    elapsed = timeit.default_timer() - start_time

    record_result("Test-B (VC-51)", "Nested JSON Traversal", elapsed)
