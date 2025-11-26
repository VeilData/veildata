from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Any, Union
import re

@dataclass
class EntitySpan:
    start: int
    end: int
    label: str
    score: float
    source: str
    text: str

class Detector(ABC):
    @abstractmethod
    def detect(self, text: str) -> List[EntitySpan]:
        pass

class RegexDetector(Detector):
    def __init__(self, patterns: Dict[str, str]):
        self.patterns = {label: re.compile(pat) for label, pat in patterns.items()}

    def detect(self, text: str) -> List[EntitySpan]:
        spans = []
        for label, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                spans.append(EntitySpan(
                    start=match.start(),
                    end=match.end(),
                    label=label,
                    score=1.0,
                    source="regex",
                    text=match.group()
                ))
        return spans

class SpacyDetector(Detector):
    def __init__(self, model: str = "en_core_web_lg", pii_labels: Optional[List[str]] = None):
        try:
            import spacy
        except ImportError:
            raise ImportError("spaCy is required for SpacyDetector. Install it with `pip install veildata[spacy]`")
        
        if not spacy.util.is_package(model):
             # Fallback or warning? For now, let spacy raise error or download
             pass
             
        try:
            self.nlp = spacy.load(model)
        except OSError:
             # Try downloading if not present? Or just fail. 
             # Better to fail with clear message.
             raise OSError(f"spaCy model '{model}' not found. Please download it with `python -m spacy download {model}`")

        self.pii_labels = set(pii_labels) if pii_labels else {
            "PERSON", "ORG", "GPE", "LOC", "NORP", "DATE", "TIME", "MONEY", "PERCENT", "FAC", "PRODUCT"
        }

    def detect(self, text: str) -> List[EntitySpan]:
        doc = self.nlp(text)
        spans = []
        for ent in doc.ents:
            if ent.label_ in self.pii_labels:
                spans.append(EntitySpan(
                    start=ent.start_char,
                    end=ent.end_char,
                    label=ent.label_,
                    score=1.0, # spaCy doesn't provide confidence scores by default easily
                    source="spacy",
                    text=ent.text
                ))
        return spans

class BertDetector(Detector):
    def __init__(self, model_name: str = "dslim/bert-base-NER", threshold: float = 0.5, label_mapping: Optional[Dict[str, List[str]]] = None):
        try:
            from transformers import pipeline
        except ImportError:
            raise ImportError("transformers and torch are required for BertDetector. Install with `pip install veildata[bert]`")
        
        self.nlp = pipeline("ner", model=model_name, aggregation_strategy="simple")
        self.threshold = threshold
        # Default mapping if none provided. 
        # dslim/bert-base-NER uses PER, ORG, LOC, MISC
        self.label_mapping = label_mapping or {
            "PERSON": ["PER"],
            "ORG": ["ORG"],
            "LOC": ["LOC"],
            "MISC": ["MISC"]
        }
        # Reverse mapping for easy lookup
        self.tag_to_pii = {}
        for pii_type, tags in self.label_mapping.items():
            for tag in tags:
                self.tag_to_pii[tag] = pii_type

    def detect(self, text: str) -> List[EntitySpan]:
        results = self.nlp(text)
        spans = []
        for res in results:
            score = float(res['score'])
            if score < self.threshold:
                continue
            
            # Map model label to PII label
            model_label = res['entity_group']
            pii_label = self.tag_to_pii.get(model_label, model_label)

            spans.append(EntitySpan(
                start=res['start'],
                end=res['end'],
                label=pii_label,
                score=res['score'],
                source="bert",
                text=res['word'] # 'word' in aggregation_strategy='simple' is the full entity text
            ))
        return spans

class HybridDetector(Detector):
    def __init__(self, detectors: List[Detector], strategy: str = "union", prefer: str = "ml"):
        self.detectors = detectors
        self.strategy = strategy
        self.prefer = prefer

    def detect(self, text: str) -> List[EntitySpan]:
        all_spans = []
        for detector in self.detectors:
            all_spans.extend(detector.detect(text))
        
        return self._merge_spans(all_spans)

    def _merge_spans(self, spans: List[EntitySpan]) -> List[EntitySpan]:
        if not spans:
            return []
        
        # Sort by start position
        spans.sort(key=lambda x: (x.start, -x.end)) # Longest first if starts match
        
        merged = []
        current_span = spans[0]
        
        for next_span in spans[1:]:
            # Check for overlap
            if next_span.start < current_span.end:
                # Overlap detected. Resolve conflict.
                current_span = self._resolve_conflict(current_span, next_span)
            else:
                merged.append(current_span)
                current_span = next_span
        
        merged.append(current_span)
        return merged

    def _resolve_conflict(self, span1: EntitySpan, span2: EntitySpan) -> EntitySpan:
        # Simple resolution logic for now
        
        # If one contains the other, keep the larger one? 
        # Or if prefer='ml', keep the ML one?
        
        is_span1_ml = span1.source in ["spacy", "bert"]
        is_span2_ml = span2.source in ["spacy", "bert"]
        
        if self.prefer == "ml":
            if is_span1_ml and not is_span2_ml:
                return span1
            if is_span2_ml and not is_span1_ml:
                return span2
        elif self.prefer == "rules":
             if not is_span1_ml and is_span2_ml:
                return span1
             if not is_span2_ml and is_span1_ml:
                return span2
        
        # Default: Keep the one with higher score, or longer length if scores equal
        if span1.score > span2.score:
            return span1
        elif span2.score > span1.score:
            return span2
        
        if (span1.end - span1.start) >= (span2.end - span2.start):
            return span1
        return span2
