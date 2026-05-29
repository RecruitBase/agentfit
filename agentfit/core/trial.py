"""
Governance types for research-grounded agent evaluation.

Grounded in: "Evaluating AI Agents" — the key conceptual shifts applied here:

  1. GovernanceDecision  — binary PASS/FAIL against BNP thresholds.
     Continuous scores survive as sub-metric evidence, not the headline.

  2. ReliabilityResult   — Pass@k (capability: at least one trial passes) and
     Pass^k (reliability: every trial passes).  Enterprise autonomous workflows
     must require Pass^k; human-in-the-loop workflows may accept Pass@k.

  3. HarnessSnapshot     — versioned capture of the evaluation environment
     (model, temperature, tools, scenario, k_trials) so re-runs are comparable.

  4. FailureMode         — structured per-trial failure records that accumulate
     into a reusable regression suite over time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Harness Snapshot
# ---------------------------------------------------------------------------

@dataclass
class HarnessSnapshot:
    """
    Immutable record of everything that could affect evaluation reproducibility.

    Stored alongside every EvaluationResult so that re-runs on a later date
    can be compared fairly — or flagged as incomparable when the harness changed.
    """

    agent_id: str
    agent_framework: str          # "openai", "vllm", "mock", …
    model: Optional[str] = None
    temperature: Optional[float] = None
    tools_available: List[str] = field(default_factory=list)
    scenario_id: str = ""
    k_trials: int = 1
    agentfit_version: str = "0.2.0"
    captured_at: str = ""         # ISO-8601, set by evaluator

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_framework": self.agent_framework,
            "model": self.model,
            "temperature": self.temperature,
            "tools_available": self.tools_available,
            "scenario_id": self.scenario_id,
            "k_trials": self.k_trials,
            "agentfit_version": self.agentfit_version,
            "captured_at": self.captured_at,
        }


# ---------------------------------------------------------------------------
# Failure Mode
# ---------------------------------------------------------------------------

@dataclass
class FailureMode:
    """
    Structured record of one observed failure.

    Accumulates across trials and evaluations into a taxonomy the team can
    tag, prioritise, and promote to permanent regression scenarios.
    """

    dimension: str
    trial_num: int
    description: str                    # human-readable cause
    scenario_id: str = ""
    trace: Optional[str] = None         # raw agent output or stack trace
    tags: List[str] = field(default_factory=list)   # e.g. ["tool_selection", "prompt_injection"]
    severity: str = "medium"            # "low" | "medium" | "high" | "critical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "trial_num": self.trial_num,
            "description": self.description,
            "scenario_id": self.scenario_id,
            "trace": self.trace,
            "tags": self.tags,
            "severity": self.severity,
        }


# ---------------------------------------------------------------------------
# Reliability Result
# ---------------------------------------------------------------------------

@dataclass
class ReliabilityResult:
    """
    Pass@k and Pass^k reliability statistics for one dimension across k trials.

    Pass@k  (capability)  — at least one of the k trials passed.
            Appropriate for human-in-the-loop workflows where a human can
            select the best output.  Formula: 1 if any trial passed, else 0.

    Pass^k  (reliability) — every trial passed (strict autonomous reliability).
            Required for autonomous workflows with no human review.
            Formula: C(c,k)/C(n,k) per the paper. When n==k this reduces to
            1.0 iff c==k, 0.0 otherwise. We store the generalised value for
            when n > k sampling is added in the future.

    dispersion — std-dev of per-trial scores, surfaced as a band, not hidden
                 in an average.
    """

    dimension: str
    k: int                            # trials executed
    passes: int                       # trials where dimension.passed == True
    trial_scores: List[float] = field(default_factory=list)

    # Computed fields — set by _compute() after construction
    pass_at_k: float = 0.0            # 1.0 or 0.0
    pass_all_k: float = 0.0           # C(c,k)/C(n,k), simplified when n==k
    dispersion: float = 0.0           # std-dev of trial_scores

    def __post_init__(self) -> None:
        self._compute()

    def _compute(self) -> None:
        n, c, k = self.k, self.passes, self.k  # n == k in our implementation

        # Pass@k: capability — at least one pass
        self.pass_at_k = 1.0 if c >= 1 else 0.0

        # Pass^k: reliability — all pass (strict) using combinatorial formula
        # C(c, k) / C(n, k).  When c < k → 0.  When c == n == k → 1.
        if c >= k and n >= k:
            self.pass_all_k = _comb(c, k) / _comb(n, k)
        else:
            self.pass_all_k = 0.0

        # Dispersion
        if len(self.trial_scores) > 1:
            mean = sum(self.trial_scores) / len(self.trial_scores)
            variance = sum((s - mean) ** 2 for s in self.trial_scores) / len(self.trial_scores)
            self.dispersion = math.sqrt(variance)
        else:
            self.dispersion = 0.0

    def reliability_label(self, mode: str = "pass_at_k") -> str:
        """Human-readable label for the binding reliability metric."""
        val = self.pass_all_k if mode == "pass_all_k" else self.pass_at_k
        pct = f"{val * 100:.0f}%"
        return f"{'PASS' if val == 1.0 else 'FAIL'} ({pct})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "k_trials": self.k,
            "passes": self.passes,
            "trial_scores": self.trial_scores,
            "pass_at_k": self.pass_at_k,
            "pass_all_k": self.pass_all_k,
            "dispersion": round(self.dispersion, 4),
        }


def _comb(n: int, k: int) -> float:
    """Binomial coefficient C(n, k) as float."""
    if k > n or k < 0:
        return 0.0
    return float(math.comb(n, k))


# ---------------------------------------------------------------------------
# Threshold Result (per dimension)
# ---------------------------------------------------------------------------

@dataclass
class ThresholdResult:
    """Whether one dimension met its BNP-defined pass threshold."""

    dimension: str
    score: float                  # mean score across trials
    threshold: float              # BNP-required minimum
    met: bool                     # score >= threshold
    reliability_mode: str = "pass_at_k"
    reliability_value: float = 0.0   # pass_at_k or pass_all_k depending on mode
    lifecycle: str = "capability"    # "capability" or "regression"

    @property
    def is_regression_failure(self) -> bool:
        """True when a regression scenario starts failing — needs immediate alert."""
        return self.lifecycle == "regression" and not self.met

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": round(self.score, 4),
            "threshold": self.threshold,
            "met": self.met,
            "reliability_mode": self.reliability_mode,
            "reliability_value": round(self.reliability_value, 4),
            "lifecycle": self.lifecycle,
            "regression_failure": self.is_regression_failure,
        }


# ---------------------------------------------------------------------------
# Governance Decision
# ---------------------------------------------------------------------------

@dataclass
class GovernanceDecision:
    """
    The headline output of an AgentFit evaluation.

    Replaces "overall_score: 0.74" with a binary deploy/block decision
    anchored to the thresholds the organisation defined in their BNP.

    The continuous score is still available as supporting evidence in
    EvaluationResult.overall_score, but governance artifacts should
    surface this decision, not the float.
    """

    decision: str                               # "PASS" or "FAIL"
    failing_dimensions: List[str] = field(default_factory=list)
    regression_failures: List[str] = field(default_factory=list)
    threshold_results: Dict[str, ThresholdResult] = field(default_factory=dict)
    rationale: str = ""

    @property
    def passed(self) -> bool:
        return self.decision == "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "passed": self.passed,
            "failing_dimensions": self.failing_dimensions,
            "regression_failures": self.regression_failures,
            "rationale": self.rationale,
            "threshold_results": {
                k: v.to_dict() for k, v in self.threshold_results.items()
            },
        }
