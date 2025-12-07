"""
Streaming redaction buffer for chunk-based processing.

This module provides a buffer that can process text in chunks while correctly
detecting and redacting entities that span across chunk boundaries.
"""

from dataclasses import dataclass
from typing import Generator, List, Optional

from veildata.pipeline import DetectionPipeline
from veildata.revealers import TokenStore


@dataclass
class ChunkMetadata:
    """Metadata about a processed chunk for debugging and tracking."""

    chunk_index: int
    input_size: int
    output_size: int
    buffer_size: int
    entities_detected: int


class StreamingRedactionBuffer:
    """
    Buffer for streaming redaction with cross-chunk entity detection.

    This class maintains a sliding window to ensure entities that span chunk
    boundaries are correctly detected and redacted. It progressively yields
    sanitized output while maintaining minimal state.

    Example:
        >>> from veildata.detectors import RegexDetector
        >>> from veildata.pipeline import DetectionPipeline
        >>> detector = RegexDetector({"EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"})
        >>> pipeline = DetectionPipeline(detector)
        >>> buffer = StreamingRedactionBuffer(pipeline, overlap_size=20)
        >>> for chunk in ["My email is john.do", "e@example.com and more"]:
        ...     output = buffer.add_chunk(chunk)
        ...     print(output, end="")
        >>> print(buffer.finalize())

    Args:
        pipeline: DetectionPipeline to use for entity detection
        overlap_size: Number of characters to retain between chunks for boundary detection
        store: Optional TokenStore to record redacted mappings
        redaction_format: Format string for redaction tokens (default: "[REDACTED_{counter}]")
    """

    def __init__(
        self,
        pipeline: DetectionPipeline,
        overlap_size: int = 512,
        store: Optional[TokenStore] = None,
        redaction_format: str = "[REDACTED_{counter}]",
    ):
        if overlap_size < 0:
            raise ValueError("overlap_size must be non-negative")

        self.pipeline = pipeline
        self.overlap_size = overlap_size
        self.store = store or pipeline.store
        self.redaction_format = redaction_format

        # Internal state
        self._buffer = ""
        self._chunk_index = 0
        self._counter = 0
        self._total_input_chars = 0
        self._total_output_chars = 0
        self._chunk_metadata: List[ChunkMetadata] = []

        # Track the absolute position in the original stream
        # This helps us map detected entities back to their original positions
        self._buffer_start_pos = 0

    def add_chunk(self, chunk: str) -> str:
        """
        Add a chunk of text and return the redacted output for the safe zone.

        The safe zone is the portion of the buffer that is guaranteed not to
        contain any entities that might continue in the next chunk.

        Args:
            chunk: New text chunk to process

        Returns:
            Redacted text for the safe portion of the buffer
        """
        if not chunk:
            return ""

        # Append new chunk to buffer
        self._buffer += chunk
        self._total_input_chars += len(chunk)

        # If buffer is smaller than overlap, we can't safely process anything yet
        if len(self._buffer) <= self.overlap_size:
            self._chunk_index += 1
            return ""

        # Calculate safe zone: everything except the overlap region
        safe_end = len(self._buffer) - self.overlap_size

        # Run detection on ENTIRE buffer (including overlap)
        # This ensures entities spanning the boundary are detected
        all_spans = self.pipeline.detector.detect(self._buffer)

        # Sort and filter overlapping spans
        all_spans.sort(key=lambda x: x.start)
        filtered_spans = []
        last_end = -1
        for span in all_spans:
            if span.start >= last_end:
                filtered_spans.append(span)
                last_end = span.end

        # Find any entities that cross the safe boundary
        # If an entity crosses into the overlap, we need to adjust safe_end
        # to stop before that entity starts
        actual_safe_end = safe_end
        for span in filtered_spans:
            # If entity starts before safe_end but ends after it, it crosses the boundary
            if span.start < safe_end < span.end:
                # Adjust safe_end to stop before this entity
                actual_safe_end = span.start
                break  # We only need to check the first crossing entity

        # Separate spans into safe zone (using actual_safe_end)
        safe_spans = [s for s in filtered_spans if s.end <= actual_safe_end]

        # Build redacted output for safe zone only
        parts = []
        current_idx = 0

        for span in safe_spans:
            # Append text before the span
            parts.append(self._buffer[current_idx : span.start])

            # Generate redaction token
            self._counter += 1
            token = self.redaction_format.format(counter=self._counter)

            # Record in store
            if self.store:
                self.store.record(token, span.text)

            # Append token
            parts.append(token)
            current_idx = span.end

        # Append remaining safe text (up to actual_safe_end)
        parts.append(self._buffer[current_idx:actual_safe_end])

        redacted_safe = "".join(parts)

        # Keep everything from actual_safe_end onward for the next iteration
        self._buffer = self._buffer[actual_safe_end:]
        self._buffer_start_pos += actual_safe_end

        # Record metadata
        output_size = len(redacted_safe)
        self._total_output_chars += output_size

        metadata = ChunkMetadata(
            chunk_index=self._chunk_index,
            input_size=len(chunk),
            output_size=output_size,
            buffer_size=len(self._buffer),
            entities_detected=len(safe_spans),
        )
        self._chunk_metadata.append(metadata)
        self._chunk_index += 1

        return redacted_safe

    def finalize(self) -> str:
        """
        Process any remaining text in the buffer.

        This should be called after all chunks have been added to ensure
        the overlap region is processed.

        Returns:
            Redacted text for the remaining buffer contents
        """
        if not self._buffer:
            return ""

        # Process all remaining text
        spans = self.pipeline.detector.detect(self._buffer)

        # Sort and filter overlapping spans
        spans.sort(key=lambda x: x.start)
        filtered_spans = []
        last_end = -1
        for span in spans:
            if span.start >= last_end:
                filtered_spans.append(span)
                last_end = span.end

        # Build redacted output
        parts = []
        current_idx = 0

        for span in filtered_spans:
            # Append text before the span
            parts.append(self._buffer[current_idx : span.start])

            # Generate redaction token
            self._counter += 1
            token = self.redaction_format.format(counter=self._counter)

            # Record in store
            if self.store:
                self.store.record(token, span.text)

            # Append token
            parts.append(token)
            current_idx = span.end

        # Append remaining text
        parts.append(self._buffer[current_idx:])

        redacted_remaining = "".join(parts)

        # Update stats
        self._total_output_chars += len(redacted_remaining)

        # Clear buffer
        self._buffer = ""

        return redacted_remaining

    def get_metadata(self) -> List[ChunkMetadata]:
        """
        Get metadata about all processed chunks.

        Returns:
            List of ChunkMetadata objects
        """
        return list(self._chunk_metadata)

    def get_stats(self) -> dict:
        """
        Get statistics about the streaming process.

        Returns:
            Dictionary with processing statistics
        """
        return {
            "total_chunks": self._chunk_index,
            "total_input_chars": self._total_input_chars,
            "total_output_chars": self._total_output_chars,
            "total_entities_redacted": self._counter,
            "buffer_size": len(self._buffer),
            "compression_ratio": (
                self._total_output_chars / self._total_input_chars
                if self._total_input_chars > 0
                else 1.0
            ),
        }

    def reset(self) -> None:
        """Reset the buffer to initial state."""
        self._buffer = ""
        self._chunk_index = 0
        self._counter = 0
        self._total_input_chars = 0
        self._total_output_chars = 0
        self._chunk_metadata.clear()
        self._buffer_start_pos = 0
        if self.store:
            self.store.clear()


def stream_redact(
    chunks: Generator[str, None, None],
    pipeline: DetectionPipeline,
    overlap_size: int = 512,
    store: Optional[TokenStore] = None,
) -> Generator[str, None, None]:
    """
    Convenience function for streaming redaction.

    This is a simple wrapper around StreamingRedactionBuffer for common use cases.

    Args:
        chunks: Generator yielding text chunks
        pipeline: DetectionPipeline to use for entity detection
        overlap_size: Number of characters to retain between chunks
        store: Optional TokenStore to record redacted mappings

    Yields:
        Redacted text chunks

    Example:
        >>> def read_file_chunks(filepath, chunk_size=4096):
        ...     with open(filepath, 'r') as f:
        ...         while True:
        ...             chunk = f.read(chunk_size)
        ...             if not chunk:
        ...                 break
        ...             yield chunk
        >>>
        >>> from veildata.engine import build_redactor
        >>> redactor, store = build_redactor(method="regex")
        >>> for redacted_chunk in stream_redact(read_file_chunks("input.txt"), redactor):
        ...     print(redacted_chunk, end="")
    """
    buffer = StreamingRedactionBuffer(pipeline, overlap_size, store)

    for chunk in chunks:
        output = buffer.add_chunk(chunk)
        if output:
            yield output

    # Don't forget the final chunk
    final_output = buffer.finalize()
    if final_output:
        yield final_output
