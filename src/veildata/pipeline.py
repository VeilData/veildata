from typing import Dict, Optional

from veildata.core import Module
from veildata.detectors import Detector
from veildata.revealers import TokenStore


class DetectionPipeline(Module):
    """
    Pipeline that uses a Detector to find entities and redacts them.
    """

    def __init__(
        self,
        detector: Detector,
        store: Optional[TokenStore] = None,
        redaction_format: str = "[REDACTED_{counter}]",
    ):
        super().__init__()
        self.detector = detector
        self.store = store
        self.redaction_format = redaction_format
        self.counter = 0

    def explain(self, text: str) -> Dict:
        """
        Run detection and return explanation of what was detected.

        Returns:
            Dict with 'original' text and 'detections' list containing metadata
            for each detected span.
        """
        spans = self.detector.detect(text)

        # Sort spans by start position
        spans.sort(key=lambda x: x.start)

        # Filter overlapping spans
        filtered_spans = []
        last_end = -1
        for span in spans:
            if span.start >= last_end:
                filtered_spans.append(span)
                last_end = span.end

        detections = []
        for span in filtered_spans:
            detections.append(
                {
                    "start": span.start,
                    "end": span.end,
                    "text": span.text,
                    "label": span.label,
                    "detector": span.source,
                    "score": span.score,
                }
            )

        return {
            "original": text,
            "detections": detections,
        }

    def forward(self, text: str) -> str:
        spans = self.detector.detect(text)

        # Ensure spans are sorted by start
        spans.sort(key=lambda x: x.start)

        # Filter out overlapping spans if any remain (simple greedy strategy)
        # HybridDetector should handle this, but good to be safe.
        filtered_spans = []
        last_end = -1
        for span in spans:
            if span.start >= last_end:
                filtered_spans.append(span)
                last_end = span.end

        parts = []
        current_idx = 0

        for span in filtered_spans:
            # Append text before the span
            parts.append(text[current_idx : span.start])

            # Generate redaction token
            self.counter += 1
            token = self.redaction_format.format(counter=self.counter)

            # Record in store
            if self.store:
                self.store.record(token, span.text)

            # Append token
            parts.append(token)

            current_idx = span.end

        # Append remaining text
        parts.append(text[current_idx:])

        return "".join(parts)
