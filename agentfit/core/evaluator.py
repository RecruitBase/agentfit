"""
Core Evaluation Engine.

Orchestrates dimension evaluations across k independent trials, computes
Pass@k / Pass^k reliability statistics, applies BNP governance thresholds,
and produces a GovernanceDecision (PASS/FAIL) as the headline output.

Continuous sub-metric scores remain available as supporting evidence and
for tracking deltas over time, but the top-line output is a binary decision
anchored to the thresholds the organisation defined in their BNP.

Research grounding:
  - Binary governance decisions produce higher inter-rater reliability than
    continuous floats (central tendency bias, subjectivity of 0.74 vs 0.75).
  - Pass@k vs Pass^k: capability vs reliability — enterprise autonomous
    workflows must require Pass^k; human-in-the-loop may accept Pass@k.
  - Harness snapshots: the evaluation environment is part of what is being
    measured and must be versioned for comparable re-runs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import asyncio
from loguru import logger

from agentfit.core.dimension import Dimension, DimensionResult, DimensionRegistry, DimensionConfig
from agentfit.core.trial import (
    GovernanceDecision,
    HarnessSnapshot,
    ReliabilityResult,
    ThresholdResult,
    FailureMode,
)
from agentfit.bnp.schema import BNPProfile

if TYPE_CHECKING:
    from agentfit.interpretability.config import InterpretabilityConfig
    from agentfit.interpretability.interpreter import InterpretationResult

_DEFAULT_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Request / Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EvaluationRequest:
    """Request for agent evaluation."""

    agent_id: str
    agent_interface: Any                      # callable or adapter.to_agent_interface()
    scenario: Dict[str, Any]
    bnp_profile: Optional[BNPProfile] = None
    dimensions: Optional[List[str]] = None    # None → all / BNP-specified
    context: Dict[str, Any] = field(default_factory=dict)
    interpretability: Optional["InterpretabilityConfig"] = None

    # Reliability: number of independent trials.  Overrides BNP k_trials when set.
    k_trials: Optional[int] = None

    # Harness metadata (model name, temperature, etc.)
    harness: Optional[HarnessSnapshot] = None

    def __post_init__(self):
        if not self.agent_id:
            raise ValueError("agent_id is required")

    @property
    def effective_k(self) -> int:
        """Resolved number of trials: request-level → BNP-level → 1."""
        if self.k_trials is not None:
            return max(1, self.k_trials)
        if self.bnp_profile is not None:
            return self.bnp_profile.k_trials
        return 1


@dataclass
class EvaluationResult:
    """Complete evaluation result across all dimensions and k trials."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    scenario_id: str = ""

    # Timing
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    total_duration_ms: float = 0.0

    # Per-dimension results (mean across trials when k > 1)
    dimension_results: Dict[str, DimensionResult] = field(default_factory=dict)

    # Supporting evidence — continuous aggregate score (0–1)
    overall_score: float = 0.0

    # ── Governance (headline output) ──────────────────────────────────────
    governance: Optional[GovernanceDecision] = None

    # Reliability (populated when k_trials > 1)
    reliability: Dict[str, ReliabilityResult] = field(default_factory=dict)

    # Failure modes observed across all trials
    failure_modes: List[FailureMode] = field(default_factory=list)

    # Harness snapshot for reproducibility auditing
    harness_snapshot: Optional[HarnessSnapshot] = None

    # Backward-compatible shim
    @property
    def passed(self) -> bool:
        if self.governance is not None:
            return self.governance.passed
        return self.overall_score >= _DEFAULT_THRESHOLD

    # Interpretation (populated when interpretability is enabled)
    interpretation: Optional["InterpretationResult"] = None

    # Metadata
    bnp_profile_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Helpers ───────────────────────────────────────────────────────────

    def add_dimension_result(self, dimension_id: str, result: DimensionResult) -> None:
        self.dimension_results[dimension_id] = result

    def compute_overall_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        if not self.dimension_results:
            return 0.0
        if weights is None:
            weights = {d: 1.0 / len(self.dimension_results) for d in self.dimension_results}
        total, total_w = 0.0, 0.0
        for dim_id, result in self.dimension_results.items():
            w = weights.get(dim_id, 0.0)
            if w > 0:
                total += result.score * w
                total_w += w
        return total / total_w if total_w else 0.0

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "agent_id": self.agent_id,
            "scenario_id": self.scenario_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            # Governance decision is the headline
            "governance": self.governance.to_dict() if self.governance else None,
            # Continuous score as supporting evidence
            "overall_score": self.overall_score,
            "overall_percentage": self.overall_score * 100,
            "passed": self.passed,
            "dimension_results": {
                k: v.to_dict() for k, v in self.dimension_results.items()
            },
            "reliability": {
                k: v.to_dict() for k, v in self.reliability.items()
            },
            "failure_modes": [f.to_dict() for f in self.failure_modes],
            "harness_snapshot": self.harness_snapshot.to_dict() if self.harness_snapshot else None,
            "bnp_profile_id": self.bnp_profile_id,
            "metadata": self.metadata,
        }
        if self.interpretation is not None:
            data["interpretation"] = self.interpretation.to_dict()
        return data


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class Evaluator:
    """
    Main evaluation engine.

    Runs k independent trials, computes per-dimension Pass@k / Pass^k
    reliability statistics, applies BNP governance thresholds, and returns
    a GovernanceDecision as the headline output alongside sub-metric evidence.
    """

    def __init__(self):
        self.registry = DimensionRegistry

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Run evaluation.

        When request.effective_k == 1 the behaviour is identical to the
        original single-trial flow (backward-compatible).
        When k > 1, k trials are run with different seeds and Pass@k / Pass^k
        statistics are computed per dimension.
        """
        import time
        start = time.time()

        result = EvaluationResult(
            agent_id=request.agent_id,
            scenario_id=request.scenario.get("id", "unknown"),
            bnp_profile_id=request.bnp_profile.id if request.bnp_profile else None,
        )

        # Attach / build harness snapshot
        result.harness_snapshot = self._build_harness_snapshot(request)

        dimensions_to_eval = self._select_dimensions(request)
        if not dimensions_to_eval:
            logger.warning(f"No dimensions to evaluate for {request.agent_id}")
            result.governance = GovernanceDecision(
                decision="FAIL",
                rationale="No dimensions were selected for evaluation.",
            )
            return result

        k = request.effective_k
        eval_context = {
            "agent": request.agent_interface,
            "scenario": request.scenario,
            "bnp": request.bnp_profile,
            "context": request.context,
        }

        # ── Run k trials ──────────────────────────────────────────────────
        all_trial_results: List[Dict[str, DimensionResult]] = []
        for trial_idx in range(k):
            trial_results = await self._run_single_trial(
                dimensions_to_eval, eval_context, request.bnp_profile, trial_idx
            )
            all_trial_results.append(trial_results)

        # ── Aggregate across trials ───────────────────────────────────────
        result.dimension_results = self._aggregate_trials(all_trial_results, dimensions_to_eval)

        # ── Collect failure modes ─────────────────────────────────────────
        result.failure_modes = self._collect_failure_modes(
            all_trial_results, request.scenario.get("id", "unknown")
        )

        # ── Compute overall weighted score (supporting evidence) ──────────
        weights = request.bnp_profile.get_dimension_weights() if request.bnp_profile else None
        result.overall_score = result.compute_overall_score(weights)

        # ── Reliability statistics (only when k > 1) ──────────────────────
        if k > 1:
            result.reliability = self._compute_reliability(all_trial_results, dimensions_to_eval)

        # ── Governance decision (headline) ────────────────────────────────
        result.governance = self._make_governance_decision(
            result, request.bnp_profile, k, result.reliability
        )

        # ── Timing ───────────────────────────────────────────────────────
        result.total_duration_ms = (time.time() - start) * 1000
        result.completed_at = datetime.now(timezone.utc).isoformat()

        # ── LLM interpretation pass ───────────────────────────────────────
        if request.interpretability and request.interpretability.enabled:
            result.interpretation = await self._run_interpretation(
                result, request.bnp_profile, weights, request.interpretability
            )

        return result

    # ------------------------------------------------------------------
    # Trial execution
    # ------------------------------------------------------------------

    async def _run_single_trial(
        self,
        dimensions: List[str],
        context: Dict[str, Any],
        bnp: Optional[BNPProfile],
        trial_idx: int,
    ) -> Dict[str, DimensionResult]:
        tasks = [
            self._evaluate_dimension(dim_id, context, bnp)
            for dim_id in dimensions
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        trial: Dict[str, DimensionResult] = {}
        for dim_id, res in zip(dimensions, results_list):
            if isinstance(res, Exception):
                logger.error(f"Dimension {dim_id} trial {trial_idx} failed: {res}")
            elif res is not None:
                trial[dim_id] = res
        return trial

    async def _evaluate_dimension(
        self,
        dimension_id: str,
        context: Dict[str, Any],
        bnp: Optional[BNPProfile],
    ) -> Optional[DimensionResult]:
        config = None
        if bnp:
            cfg_dict = bnp.get_dimension_config(dimension_id)
            config = DimensionConfig(**cfg_dict) if cfg_dict else None

        dimension = self.registry.create_instance(dimension_id, config)
        if not dimension:
            logger.warning(f"Dimension {dimension_id} not found in registry")
            return None

        if not await dimension.validate_input(context):
            logger.warning(f"Input validation failed for dimension {dimension_id}")
            return None

        try:
            return await dimension.evaluate(context)
        except Exception as e:
            logger.error(f"Error evaluating {dimension_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate_trials(
        self,
        all_trials: List[Dict[str, DimensionResult]],
        dimensions: List[str],
    ) -> Dict[str, DimensionResult]:
        """Compute mean score and majority-vote passed across k trials."""
        if len(all_trials) == 1:
            return all_trials[0]

        aggregated: Dict[str, DimensionResult] = {}
        for dim_id in dimensions:
            trial_results = [t[dim_id] for t in all_trials if dim_id in t]
            if not trial_results:
                continue
            mean_score = sum(r.score for r in trial_results) / len(trial_results)
            passes = sum(1 for r in trial_results if r.passed)
            majority_passed = passes > len(trial_results) / 2

            # Use first trial as structural base, override with aggregated values
            base = trial_results[0]
            base.score = mean_score
            base.passed = majority_passed
            base.feedback = (
                f"[{len(trial_results)} trials] mean={mean_score:.2f}, "
                f"passed={passes}/{len(trial_results)}. {base.feedback}"
            )
            aggregated[dim_id] = base

        return aggregated

    def _collect_failure_modes(
        self,
        all_trials: List[Dict[str, DimensionResult]],
        scenario_id: str,
    ) -> List[FailureMode]:
        failures: List[FailureMode] = []
        for trial_idx, trial in enumerate(all_trials):
            for dim_id, result in trial.items():
                if not result.passed:
                    failures.append(FailureMode(
                        dimension=dim_id,
                        trial_num=trial_idx + 1,
                        description=result.feedback or "Dimension did not pass threshold",
                        scenario_id=scenario_id,
                        trace=result.error,
                        severity="high" if "safety" in dim_id else "medium",
                    ))
        return failures

    # ------------------------------------------------------------------
    # Reliability
    # ------------------------------------------------------------------

    def _compute_reliability(
        self,
        all_trials: List[Dict[str, DimensionResult]],
        dimensions: List[str],
    ) -> Dict[str, ReliabilityResult]:
        reliability: Dict[str, ReliabilityResult] = {}
        for dim_id in dimensions:
            trial_results = [t[dim_id] for t in all_trials if dim_id in t]
            if not trial_results:
                continue
            k = len(trial_results)
            passes = sum(1 for r in trial_results if r.passed)
            scores = [r.score for r in trial_results]
            reliability[dim_id] = ReliabilityResult(
                dimension=dim_id,
                k=k,
                passes=passes,
                trial_scores=scores,
            )
        return reliability

    # ------------------------------------------------------------------
    # Governance decision
    # ------------------------------------------------------------------

    def _make_governance_decision(
        self,
        result: EvaluationResult,
        bnp: Optional[BNPProfile],
        k: int,
        reliability: Dict[str, ReliabilityResult],
    ) -> GovernanceDecision:
        thresholds = bnp.get_dimension_thresholds() if bnp else {}
        rel_modes = bnp.get_dimension_reliability_modes() if bnp else {}
        lifecycles = bnp.get_dimension_lifecycles() if bnp else {}

        threshold_results: Dict[str, ThresholdResult] = {}
        failing: List[str] = []
        regression_fails: List[str] = []

        for dim_id, dim_result in result.dimension_results.items():
            threshold = thresholds.get(dim_id, _DEFAULT_THRESHOLD)
            rel_mode = rel_modes.get(dim_id, "pass_at_k")
            lifecycle = lifecycles.get(dim_id, "capability")

            # When k > 1, use the reliability metric as the binding signal
            rel_value = dim_result.score  # single-trial: plain score
            if k > 1 and dim_id in reliability:
                rel = reliability[dim_id]
                rel_value = rel.pass_all_k if rel_mode == "pass_all_k" else rel.pass_at_k
                met = rel_value >= threshold
            else:
                met = dim_result.score >= threshold

            tr = ThresholdResult(
                dimension=dim_id,
                score=dim_result.score,
                threshold=threshold,
                met=met,
                reliability_mode=rel_mode,
                reliability_value=rel_value,
                lifecycle=lifecycle,
            )
            threshold_results[dim_id] = tr

            if not met:
                failing.append(dim_id)
            if tr.is_regression_failure:
                regression_fails.append(dim_id)

        decision = "PASS" if not failing else "FAIL"

        if not failing:
            rationale = f"All {len(threshold_results)} dimension(s) met their thresholds."
        else:
            parts = []
            for dim_id in failing:
                tr = threshold_results[dim_id]
                parts.append(
                    f"{dim_id}: {tr.score:.2f} < threshold {tr.threshold:.2f}"
                )
            rationale = "FAIL on: " + "; ".join(parts)
            if regression_fails:
                rationale += f". REGRESSION ALERT: {', '.join(regression_fails)}"

        return GovernanceDecision(
            decision=decision,
            failing_dimensions=failing,
            regression_failures=regression_fails,
            threshold_results=threshold_results,
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _select_dimensions(self, request: EvaluationRequest) -> List[str]:
        if request.dimensions:
            return request.dimensions
        if request.bnp_profile and request.bnp_profile.evaluation_dimensions:
            return [d.dimension for d in request.bnp_profile.evaluation_dimensions]
        return self.registry.list_available()

    def _build_harness_snapshot(self, request: EvaluationRequest) -> HarnessSnapshot:
        if request.harness:
            snap = request.harness
        else:
            snap = HarnessSnapshot(
                agent_id=request.agent_id,
                agent_framework="unknown",
                scenario_id=request.scenario.get("id", "unknown"),
                k_trials=request.effective_k,
            )

        # Infer framework from adapter if possible
        agent = request.agent_interface
        if hasattr(agent, "__self__"):
            adapter = agent.__self__
            snap.agent_framework = getattr(adapter, "framework", snap.agent_framework)
            snap.model = getattr(adapter, "model", snap.model)

        snap.tools_available = request.scenario.get("expected_tools", [])
        snap.captured_at = datetime.now(timezone.utc).isoformat()
        snap.k_trials = request.effective_k
        return snap

    async def _run_interpretation(
        self,
        result: EvaluationResult,
        bnp: Optional[BNPProfile],
        weights: Optional[Dict[str, float]],
        config: "InterpretabilityConfig",
    ) -> Optional["InterpretationResult"]:
        from agentfit.interpretability.interpreter import Interpreter
        try:
            return await Interpreter(config).interpret(result, bnp, weights)
        except Exception as e:
            logger.error(f"Interpretation failed: {e}")
            return None
