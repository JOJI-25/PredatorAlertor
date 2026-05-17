"""
PredatorAlert Classification Module
Determines predator vs safe animals and assigns priority levels.
"""
from dataclasses import dataclass
from typing import Optional
from detector import Detection
from config import PREDATOR_ANIMALS, SAFE_ANIMALS, PREDATOR_PRIORITY, DEFAULT_PRIORITY


@dataclass
class ClassifiedDetection:
    """A detection with classification and priority information."""
    class_name: str
    confidence: float
    is_predator: bool
    priority: Optional[int]
    bbox: tuple[int, int, int, int]
    
    @property
    def is_safe(self) -> bool:
        """Check if this is a safe (non-predator) animal."""
        return not self.is_predator
    
    @property
    def priority_label(self) -> str:
        """Human-readable priority label."""
        if self.priority is None:
            return "none"
        priority_labels = {
            1: "critical",
            2: "high",
            3: "medium",
            4: "low"
        }
        return priority_labels.get(self.priority, "unknown")


class AnimalClassifier:
    """Classifies detected animals as predator or safe."""
    
    def __init__(self):
        self.predators = PREDATOR_ANIMALS
        self.safe_animals = SAFE_ANIMALS
        self.priority_map = PREDATOR_PRIORITY
    
    def classify(self, detection: Detection) -> ClassifiedDetection:
        """
        Classify a detection as predator or safe animal.
        Returns ClassifiedDetection with priority if predator.
        """
        class_name = self._normalize_class_name(detection.class_name)
        
        # Check if predator
        is_predator = class_name in self.predators
        
        # Assign priority for predators
        priority = None
        if is_predator:
            priority = self.priority_map.get(class_name, DEFAULT_PRIORITY)
        
        return ClassifiedDetection(
            class_name=class_name,
            confidence=detection.confidence,
            is_predator=is_predator,
            priority=priority,
            bbox=detection.bbox
        )
    
    def classify_batch(self, detections: list[Detection]) -> list[ClassifiedDetection]:
        """Classify multiple detections."""
        return [self.classify(d) for d in detections]
    
    def _normalize_class_name(self, name: str) -> str:
        """
        Normalize class name for consistent matching.
        Handles variations like 'Lion', 'LION', 'African Lion' etc.
        """
        # Lowercase and replace separators
        normalized = name.lower().strip()
        normalized = normalized.replace("-", "_").replace(" ", "_")
        
        # Handle common wildlife model class name variations
        name_mappings = {
            "african_lion": "lion",
            "bengal_tiger": "tiger",
            "siberian_tiger": "tiger",
            "grizzly_bear": "bear",
            "brown_bear": "bear",
            "black_bear": "bear",
            "polar_bear": "bear",
            "gray_wolf": "wolf",
            "grey_wolf": "wolf",
            "red_fox": "fox",
            "arctic_fox": "fox",
            "wild_pig": "pig",
            "african_elephant": "elephant",
            "asian_elephant": "elephant",
            "wild-boar": "wild_boar",
        }
        
        return name_mappings.get(normalized, normalized)
    
    def is_known_animal(self, class_name: str) -> bool:
        """Check if the class name is a known animal (predator or safe)."""
        normalized = self._normalize_class_name(class_name)
        return normalized in self.predators or normalized in self.safe_animals
    
    def get_predators_only(self, classified: list[ClassifiedDetection]) -> list[ClassifiedDetection]:
        """Filter to return only predator detections."""
        return [c for c in classified if c.is_predator]
    
    def get_safe_only(self, classified: list[ClassifiedDetection]) -> list[ClassifiedDetection]:
        """Filter to return only safe animal detections."""
        return [c for c in classified if c.is_safe]
    
    def sort_by_priority(self, classified: list[ClassifiedDetection]) -> list[ClassifiedDetection]:
        """Sort predators by priority (1 = most critical first)."""
        return sorted(
            classified,
            key=lambda x: (x.priority if x.priority is not None else 999, -x.confidence)
        )
