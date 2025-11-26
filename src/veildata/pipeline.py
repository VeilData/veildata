from typing import Optional, List
from veildata.core import Module
from veildata.detectors import Detector, EntitySpan
from veildata.revealers import TokenStore

class DetectionPipeline(Module):
    """
    Pipeline that uses a Detector to find entities and masks them.
    """
    def __init__(
        self, 
        detector: Detector, 
        store: Optional[TokenStore] = None,
        mask_format: str = "[REDACTED_{counter}]"
    ):
        super().__init__()
        self.detector = detector
        self.store = store
        self.mask_format = mask_format
        self.counter = 0

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
            parts.append(text[current_idx:span.start])
            
            # Generate mask token
            self.counter += 1
            token = self.mask_format.format(counter=self.counter)
            
            # Record in store
            if self.store:
                self.store.record(token, span.text)
            
            # Append token
            parts.append(token)
            
            current_idx = span.end
            
        # Append remaining text
        parts.append(text[current_idx:])
        
        return "".join(parts)
