"""
Core Evaluation Engine.

Orchestrates dimension evaluations, aggregates results, and produces
comprehensive evaluation reports driven by BNP profiles.  Optionally
runs an LLM-powered interpretability pass that explains scores in the
context of the Business Need Profile.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio
from loguru import logger

from agentfit.core.dimension import Dimension, DimensionResult, DimensionRegistry, DimensionConfig
from agentfit.bnp.schema import BNPProfile

if TYPE_CHECKING:
    from agentfit.interpretability.config import InterpretabilityConfig
    from agentfit.interpretability.interpreter import InterpretationResult


@dataclass
class EvaluationRequest:
    """Request for agent evaluation."""
    agent_id: str
    agent_interface: Any  # Callable agent or API endpoint
    scenario: Dict[str, Any]  # Test scenario/task
    bnp_profile: Optional[BNPProfile] = None
    dimensions: Optional[List[str]] = None  # Specific dimensions to evaluate, None = all
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context
    interpretability: Optional["InterpretabilityConfig"] = None
    
    def __post_init__(self):
        if not self.agent_id:
            raise ValueError("agent_id is required")


@dataclass
class EvaluationResult:
    """Complete evaluation result across all dimensions."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    scenario_id: str = ""
    
    # Timing
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    total_duration_ms: float = 0.0
    
    # Results
    dimension_results: Dict[str, DimensionResult] = field(default_factory=dict)
    overall_score: float = 0.0
    passed: bool = False
    
    # Interpretation (populated when interpretability is enabled)
    interpretation: Optional["InterpretationResult"] = None
    
    # Metadata
    bnp_profile_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_dimension_result(self, dimension_id: str, result: DimensionResult) -> None:
        """Add a dimension result."""
        self.dimension_results[dimension_id] = result
    
    def compute_overall_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Compute weighted overall score.
        
        Args:
            weights: Dimension weights. If None, uses equal weighting.
        
        Returns:
            Overall score (0-1)
        """
        if not self.dimension_results:
            return 0.0
        
        if weights is None:
            # Equal weighting
            weights = {
                dim_id: 1.0 / len(self.dimension_results)
                for dim_id in self.dimension_results.keys()
            }
        
        total_score = 0.0
        total_weight = 0.0
        
        for dim_id, result in self.dimension_results.items():
            weight = weights.get(dim_id, 0.0)
            if weight > 0:
                total_score += result.score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return total_score / total_weight
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data: Dict[str, Any] = {
            "id": self.id,
            "agent_id": self.agent_id,
            "scenario_id": self.scenario_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "overall_score": self.overall_score,
            "overall_percentage": self.overall_score * 100,
            "passed": self.passed,
            "dimension_results": {
                dim_id: result.to_dict()
                for dim_id, result in self.dimension_results.items()
            },
            "bnp_profile_id": self.bnp_profile_id,
            "metadata": self.metadata,
        }
        if self.interpretation is not None:
            data["interpretation"] = self.interpretation.to_dict()
        return data


class Evaluator:
    """
    Main evaluation engine.
    
    Coordinates dimension evaluations, aggregates results, and applies
    BNP-driven configuration for comprehensive agent assessment.
    """
    
    def __init__(self):
        """Initialize evaluator."""
        self.registry = DimensionRegistry
        self.logger = logger
    
    async def evaluate(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResult:
        """
        Evaluate an agent against specified dimensions.
        
        Args:
            request: Evaluation request with agent and scenario
        
        Returns:
            Complete evaluation result
        """
        result = EvaluationResult(
            agent_id=request.agent_id,
            scenario_id=request.scenario.get("id", "unknown"),
            bnp_profile_id=request.bnp_profile.id if request.bnp_profile else None,
        )
        
        # Determine which dimensions to evaluate
        dimensions_to_eval = self._select_dimensions(request)
        
        if not dimensions_to_eval:
            self.logger.warning(f"No dimensions to evaluate for {request.agent_id}")
            result.overall_score = 0.0
            result.passed = False
            return result
        
        # Prepare evaluation context
        eval_context = {
            "agent": request.agent_interface,
            "scenario": request.scenario,
            "bnp": request.bnp_profile,
            "context": request.context,
        }
        
        # Run evaluations
        import time
        start_time = time.time()
        
        dimension_tasks = [
            self._evaluate_dimension(dim_id, eval_context, request.bnp_profile)
            for dim_id in dimensions_to_eval
        ]
        
        dimension_results = await asyncio.gather(*dimension_tasks, return_exceptions=True)
        
        # Collect results
        for dim_id, dim_result in zip(dimensions_to_eval, dimension_results):
            if isinstance(dim_result, Exception):
                self.logger.error(f"Dimension {dim_id} evaluation failed: {dim_result}")
                continue
            
            if dim_result is not None:
                result.add_dimension_result(dim_id, dim_result)
        
        # Compute overall score using BNP weights if available
        weights = None
        if request.bnp_profile:
            weights = request.bnp_profile.get_dimension_weights()
        
        result.overall_score = result.compute_overall_score(weights)
        
        # Determine pass/fail
        if request.bnp_profile:
            result.passed = self._check_passed(result, request.bnp_profile)
        else:
            result.passed = result.overall_score >= 0.7
        
        # Record timing
        end_time = time.time()
        result.total_duration_ms = (end_time - start_time) * 1000
        result.completed_at = datetime.utcnow().isoformat()
        
        # Run interpretability pass if configured
        if request.interpretability and request.interpretability.enabled:
            result.interpretation = await self._run_interpretation(
                result, request.bnp_profile, weights, request.interpretability
            )
        
        return result
    
    def _select_dimensions(self, request: EvaluationRequest) -> List[str]:
        """Determine which dimensions to evaluate."""
        if request.dimensions:
            return request.dimensions
        
        if request.bnp_profile:
            return [d.dimension for d in request.bnp_profile.evaluation_dimensions]
        
        return self.registry.list_available()
    
    async def _evaluate_dimension(
        self,
        dimension_id: str,
        context: Dict[str, Any],
        bnp: Optional[BNPProfile],
    ) -> Optional[DimensionResult]:
        """Evaluate a single dimension."""
        # Get dimension configuration from BNP if available
        config = None
        if bnp:
            dim_config_dict = bnp.get_dimension_config(dimension_id)
            config = DimensionConfig(**dim_config_dict) if dim_config_dict else None
        
        # Create dimension instance
        dimension = self.registry.create_instance(dimension_id, config)
        if not dimension:
            self.logger.warning(f"Dimension {dimension_id} not found in registry")
            return None
        
        # Validate input
        if not await dimension.validate_input(context):
            self.logger.warning(f"Input validation failed for dimension {dimension_id}")
            return None
        
        # Run evaluation
        try:
            result = await dimension.evaluate(context)
            return result
        except Exception as e:
            self.logger.error(f"Error evaluating dimension {dimension_id}: {e}")
            return None
    
    async def _run_interpretation(
        self,
        result: EvaluationResult,
        bnp: Optional[BNPProfile],
        weights: Optional[Dict[str, float]],
        config: "InterpretabilityConfig" = None,
    ) -> Optional["InterpretationResult"]:
        """Run LLM-powered interpretation on the completed evaluation."""
        from agentfit.interpretability.interpreter import Interpreter

        if config is None:
            return None

        try:
            interpreter = Interpreter(config)
            return await interpreter.interpret(result, bnp, weights)
        except Exception as e:
            self.logger.error(f"Interpretation failed: {e}")
            return None

    def _check_passed(self, result: EvaluationResult, bnp: BNPProfile) -> bool:
        """Check if evaluation passed BNP criteria."""
        # Check critical capabilities
        for req in bnp.requirements:
            if req.required and req.capability:
                # Find dimension result that covers this capability
                # This is a simplified check - real implementation would be more sophisticated
                if result.overall_score < (req.min_success_rate or 0.7):
                    return False
        
        return result.overall_score >= 0.7
