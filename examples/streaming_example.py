"""
Example demonstrating streaming redaction with VeilData.

This example shows how to:
1. Process large files in chunks using the streaming buffer
2. Use the streaming API endpoint
3. Handle cross-chunk entity detection
"""

from veildata.detectors import RegexDetector
from veildata.pipeline import DetectionPipeline
from veildata.revealers import TokenStore
from veildata.streaming_buffer import StreamingRedactionBuffer, stream_redact


def example_1_basic_streaming():
    """Basic example of streaming redaction."""
    print("=== Example 1: Basic Streaming ===\n")

    # Setup detector
    patterns = {
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PHONE": r"\d{3}-\d{4}",
    }
    detector = RegexDetector(patterns)
    pipeline = DetectionPipeline(detector)

    # Create buffer
    buffer = StreamingRedactionBuffer(pipeline, overlap_size=20)

    # Simulate chunks (in real use, these would come from a file or stream)
    chunks = [
        "My email is john.do",
        "e@example.com and my phone is 555-",
        "1234. Contact me anytime!",
    ]

    print("Processing chunks...")
    for i, chunk in enumerate(chunks, 1):
        output = buffer.add_chunk(chunk)
        print(f"Chunk {i}: {chunk!r}")
        print(f"  Output: {output!r}")

    final = buffer.finalize()
    print(f"Final: {final!r}\n")

    # Get stats
    stats = buffer.get_stats()
    print(f"Stats: {stats}\n")


def example_2_file_streaming():
    """Example of streaming a file."""
    print("=== Example 2: File Streaming ===\n")

    # Create a test file
    with open("test_input.txt", "w") as f:
        for i in range(10):
            f.write(f"Line {i}: Contact user{i}@example.com or call 555-{i:04d}\n")

    # Setup
    patterns = {"EMAIL": r"\S+@\S+", "PHONE": r"\d{3}-\d{4}"}
    detector = RegexDetector(patterns)
    pipeline = DetectionPipeline(detector)
    store = TokenStore()

    def read_file_chunks(filepath, chunk_size=100):
        """Generator that yields file chunks."""
        with open(filepath, "r") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    # Process using stream_redact
    print("Redacting test_input.txt...")
    output_chunks = list(
        stream_redact(
            read_file_chunks("test_input.txt"), pipeline, overlap_size=30, store=store
        )
    )

    # Write output
    with open("test_output.txt", "w") as f:
        f.write("".join(output_chunks))

    print("✓ Redacted to test_output.txt")
    print(f"✓ Found {len(store.mappings)} entities\n")

    # Show first few mappings
    for i, (token, original) in enumerate(list(store.mappings.items())[:5], 1):
        print(f"  {token} → {original}")

    print()


def example_3_api_usage():
    """Example of using the streaming API."""
    print("=== Example 3: API Usage ===\n")

    print("To use the streaming API:")
    print()
    print("1. Start the API server:")
    print("   $ uvicorn veildata.api.app:app --reload")
    print()
    print("2. Stream redaction with curl:")
    print('   $ curl -X POST "http://localhost:8000/v1/redact/stream" \\')
    print('     -H "Content-Type: text/plain" \\')
    print("     --data-binary @input.txt > output.txt")
    print()
    print("3. With custom parameters:")
    print(
        '   $ curl -X POST "http://localhost:8000/v1/redact/stream?overlap_size=256&return_store=true" \\'
    )
    print('     -H "Content-Type: text/plain" \\')
    print("     --data-binary @input.txt -v 2>&1 | grep -i x-token-store")
    print()


def example_4_cli_usage():
    """Example of using the CLI streaming mode."""
    print("=== Example 4: CLI Usage ===\n")

    print("Stream redaction from command line:")
    print()
    print("1. Basic streaming:")
    print("   $ veildata redact input.txt --stream --output output.txt")
    print()
    print("2. With custom chunk and overlap sizes:")
    print("   $ veildata redact large_file.txt --stream \\")
    print("       --chunk-size 8192 --overlap 1024 \\")
    print("       --output redacted.txt --store store.json")
    print()
    print("3. With timing and verbose output:")
    print("   $ veildata redact input.txt --stream --time --verbose \\")
    print("       --output output.txt")
    print()
    print("4. Pipe stdin:")
    print("   $ cat large_file.txt | veildata redact --stream > output.txt")
    print()


def main():
    """Run all examples."""
    example_1_basic_streaming()
    example_2_file_streaming()
    example_3_api_usage()
    example_4_cli_usage()

    print("=" * 50)
    print("Examples complete! Check test_output.txt for results.")
    print("=" * 50)


if __name__ == "__main__":
    main()
