"""
Core Dimension Framework.

Base classes and protocols for evaluation dimensions. Dimensions represent
distinct aspects of agent capability (task competence, tool use, etc.)
and can be composed into comprehensive evaluations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid


class ScoringMethod(str, Enum):
    """Scoring methodologies for dimensions."""
    BINARY = "binary"  # Pass/fail
    PERCENTAGE = "percentage"  # 0-100
    SCORE = "score"  # Arbitrary numeric
    RUBRIC = "rubric"  # Multi-level rubric


@dataclass
class Metric:
    """Individual metric within a dimension result."""
    name: str
    value: float
    max_value: float = 1.0
    unit: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_percentage(self) -> float:
        """Convert metric to percentage (0-100)."""
        if self.max_value == 0:
            return 0.0
        return (self.value / self.max_value) * 100.0


@dataclass
class DimensionResult:
    """Result from evaluating a single dimension."""
    
    dimension_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dimension_name: str = ""
    dimension_type: str = ""  # e.g., "task_competence", "tool_use"
    
    # Scoring
    score: float = 0.0  # 0-1 normalized score
    scoring_method: ScoringMethod = ScoringMethod.SCORE
    max_score: float = 1.0
    
    # Details
    metrics: List[Metric] = field(default_factory=list)
    passed: bool = False
    feedback: str = ""
    error: Optional[str] = None
    
    # Metadata
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_percentage(self) -> float:
        """Get score as percentage (0-100)."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "dimension_id": self.dimension_id,
            "dimension_name": self.dimension_name,
            "dimension_type": self.dimension_type,
            "score": self.score,
            "percentage": self.get_percentage(),
            "scoring_method": self.scoring_method.value,
            "passed": self.passed,
            "feedback": self.feedback,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "max_value": m.max_value,
                    "unit": m.unit,
                    "percentage": m.to_percentage(),
                }
                for m in self.metrics
            ],
            "metadata": self.metadata,
        }


@dataclass
class DimensionConfig:
    """Configuration for a dimension evaluator."""
    enabled: bool = True
    weight: float = 1.0
    min_score_threshold: Optional[float] = None
    timeout_seconds: Optional[int] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)


class Dimension(ABC):
    """
    Abstract base class for evaluation dimensions.
    
    Each dimension represents a distinct aspect of agent capability.
    Subclasses implement specific evaluation logic and scoring.
    """
    
    # Class attributes that subclasses should override
    dimension_id: str = "base"
    dimension_name: str = "Base Dimension"
    dimension_type: str = "base"
    description: str = ""
    scoring_method: ScoringMethod = ScoringMethod.SCORE
    
    def __init__(self, config: Optional[DimensionConfig] = None):
        """Initialize dimension with optional configuration."""
        self.config = config or DimensionConfig()
    
    @abstractmethod
    async def evaluate(self, input_data: Dict[str, Any]) -> DimensionResult:
        """
        Evaluate agent performance on this dimension.
        
        Args:
            input_data: Context and test data for evaluation
                Expected keys depend on dimension type:
                - "agent": Agent interface/callable
                - "scenario": Test scenario/task
                - "context": Additional context
                - "bnp": BNP profile if available
        
        Returns:
            DimensionResult with score, feedback, and metrics
        """
        pass
    
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data has required fields."""
        pass
    
    def _create_result(
        self,
        score: float,
        passed: bool,
        feedback: str = "",
        metrics: Optional[List[Metric]] = None,
        error: Optional[str] = None,
    ) -> DimensionResult:
        """Helper to create a DimensionResult."""
        return DimensionResult(
            dimension_name=self.dimension_name,
            dimension_type=self.dimension_type,
            score=score,
            max_score=1.0,
            scoring_method=self.scoring_method,
            passed=passed,
            feedback=feedback,
            error=error,
            metrics=metrics or [],
        )


class DimensionRegistry:
    """Registry for managing available dimensions."""
    
    _dimensions: Dict[str, type[Dimension]] = {}
    
    @classmethod
    def register(cls, dimension_class: type[Dimension]) -> None:
        """Register a dimension implementation."""
        dim_id = getattr(dimension_class, "dimension_id", dimension_class.__name__)
        cls._dimensions[dim_id] = dimension_class
    
    @classmethod
    def get(cls, dimension_id: str) -> Optional[type[Dimension]]:
        """Get a dimension implementation by ID."""
        return cls._dimensions.get(dimension_id)
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all registered dimension IDs."""
        return list(cls._dimensions.keys())
    
    @classmethod
    def create_instance(
        cls,
        dimension_id: str,
        config: Optional[DimensionConfig] = None
    ) -> Optional[Dimension]:
        """Create an instance of a registered dimension."""
        dimension_class = cls.get(dimension_id)
        if dimension_class:
            return dimension_class(config)
        return None
