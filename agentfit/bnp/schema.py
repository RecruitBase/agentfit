"""
Business Need Profile (BNP) Schema.

Defines the structure for organizations to express their agent requirements,
constraints, and evaluation priorities in a declarative format.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid


class AgentDomain(str, Enum):
    """Supported agent application domains."""
    CUSTOMER_SERVICE = "customer_service"
    TECHNICAL_SUPPORT = "technical_support"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    RESEARCH = "research"
    TASK_AUTOMATION = "task_automation"
    CREATIVE = "creative"
    GENERAL = "general"


class TaskComplexity(str, Enum):
    """Task complexity levels for agent requirements."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass(init=False)
class AgentRequirement:
    """Individual agent capability requirement."""
    capability: str
    description: str
    required: bool = True
    min_success_rate: Optional[float] = None  # 0.0-1.0
    priority: str = "medium"  # low, medium, high, critical

    def __init__(
        self,
        capability: Optional[str] = None,
        description: str = "",
        required: bool = True,
        min_success_rate: Optional[float] = None,
        priority: str = "medium",
        *,
        name: Optional[str] = None,
        criticality: Optional[str] = None,
    ):
        self.capability = capability or name or ""
        self.description = description
        self.required = required
        self.min_success_rate = min_success_rate
        self.priority = criticality or priority
        self.__post_init__()
    
    def __post_init__(self):
        if self.min_success_rate is not None:
            if not 0.0 <= self.min_success_rate <= 1.0:
                raise ValueError("min_success_rate must be between 0.0 and 1.0")

    @property
    def name(self) -> str:
        """Backward-compatible alias for capability."""
        return self.capability

    @name.setter
    def name(self, value: str) -> None:
        self.capability = value

    @property
    def criticality(self) -> str:
        """Backward-compatible alias for priority."""
        return self.priority

    @criticality.setter
    def criticality(self, value: str) -> None:
        self.priority = value


@dataclass
class DimensionWeight:
    """Evaluation dimension with weighting."""
    dimension: str
    weight: float
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight must be between 0.0 and 1.0")


@dataclass(init=False)
class BNPProfile:
    """
    Business Need Profile - declarative agent evaluation requirements.
    
    Organizations define their agent needs, constraints, and evaluation
    priorities through this profile. It drives dimension selection, weighting,
    and scenario filtering.
    """
    
    # Profile metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    organization: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    # Agent context
    agent_domain: AgentDomain = AgentDomain.GENERAL
    agent_name: Optional[str] = None
    agent_description: Optional[str] = None
    
    # Requirements and capabilities
    requirements: List[AgentRequirement] = field(default_factory=list)
    critical_capabilities: List[str] = field(default_factory=list)
    
    # Evaluation configuration
    evaluation_dimensions: List[DimensionWeight] = field(default_factory=list)
    task_complexity: TaskComplexity = TaskComplexity.MODERATE
    scenario_filters: Dict[str, Any] = field(default_factory=dict)  # Domain-specific filters
    
    # Constraints and compliance
    max_latency_ms: Optional[int] = None
    max_errors_per_task: Optional[int] = None
    compliance_requirements: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        id: Optional[str] = None,
        name: str = "",
        organization: str = "",
        description: str = "",
        created_at: str = "",
        updated_at: str = "",
        agent_domain: AgentDomain = AgentDomain.GENERAL,
        agent_name: Optional[str] = None,
        agent_description: Optional[str] = None,
        requirements: Optional[List[AgentRequirement]] = None,
        critical_capabilities: Optional[List[str]] = None,
        evaluation_dimensions: Optional[List[DimensionWeight]] = None,
        task_complexity: TaskComplexity = TaskComplexity.MODERATE,
        scenario_filters: Optional[Dict[str, Any]] = None,
        max_latency_ms: Optional[int] = None,
        max_errors_per_task: Optional[int] = None,
        compliance_requirements: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
        *,
        organization_name: Optional[str] = None,
        industry: Optional[str] = None,
        required_dimensions: Optional[List[str]] = None,
        domain: Optional[AgentDomain] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.organization = organization or organization_name or ""
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at
        self.agent_domain = domain or agent_domain
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.requirements = list(requirements or [])
        self.critical_capabilities = list(critical_capabilities or [])
        self.evaluation_dimensions = list(evaluation_dimensions or [])
        self.task_complexity = task_complexity
        self.scenario_filters = dict(scenario_filters or {})
        self.max_latency_ms = max_latency_ms
        self.max_errors_per_task = max_errors_per_task
        self.compliance_requirements = list(compliance_requirements or [])
        self.tags = list(tags or [])
        self.custom_metadata = dict(custom_metadata or {})

        if industry is not None:
            self.custom_metadata.setdefault("industry", industry)

        if required_dimensions:
            weight = 1.0 / len(required_dimensions)
            self.evaluation_dimensions.extend(
                DimensionWeight(dimension=dimension, weight=weight)
                for dimension in required_dimensions
            )
    
    def validate(self) -> bool:
        """Validate BNP profile consistency."""
        if not self.name:
            raise ValueError("Profile name is required")
        
        if not self.requirements:
            raise ValueError("At least one requirement must be specified")
        
        if self.evaluation_dimensions:
            total_weight = sum(d.weight for d in self.evaluation_dimensions)
            if not (0.99 <= total_weight <= 1.01):  # Allow small floating point errors
                raise ValueError(f"Dimension weights must sum to 1.0, got {total_weight}")
        
        return True
    
    def get_dimension_weights(self) -> Dict[str, float]:
        """Get dimension name to weight mapping."""
        return {d.dimension: d.weight for d in self.evaluation_dimensions}
    
    def get_dimension_config(self, dimension: str) -> Dict[str, Any]:
        """Get configuration for a specific dimension."""
        for d in self.evaluation_dimensions:
            if d.dimension == dimension:
                return d.config
        return {}

    @property
    def domain(self) -> str:
        """Backward-compatible string form of the agent domain."""
        return self.agent_domain.value

    @domain.setter
    def domain(self, value: Any) -> None:
        self.agent_domain = AgentDomain(value)

    @property
    def organization_name(self) -> str:
        """Backward-compatible alias for organization."""
        return self.organization

    @organization_name.setter
    def organization_name(self, value: str) -> None:
        self.organization = value

    @property
    def industry(self) -> str:
        """Backward-compatible industry metadata accessor."""
        return str(self.custom_metadata.get("industry", ""))

    @industry.setter
    def industry(self, value: str) -> None:
        self.custom_metadata["industry"] = value

    @property
    def required_dimensions(self) -> List[str]:
        """Backward-compatible list of selected dimension ids."""
        return [dimension.dimension for dimension in self.evaluation_dimensions]

    @required_dimensions.setter
    def required_dimensions(self, value: List[str]) -> None:
        if not value:
            self.evaluation_dimensions = []
            return
        weight = 1.0 / len(value)
        self.evaluation_dimensions = [
            DimensionWeight(dimension=dimension, weight=weight)
            for dimension in value
        ]


Domain = AgentDomain
