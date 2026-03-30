"""
Core Interpreter.

Orchestrates LLM-powered interpretation of evaluation results.
Takes raw scores, metrics, and BNP context, calls the configured LLM,
parses the structured response, and attaches interpretations to results.
"""

import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger

from agentfit.core.evaluator import EvaluationResult
from agentfit.bnp.schema import BNPProfile
from agentfit.interpretability.config import InterpretabilityConfig
from agentfit.interpretability.llm_client import llm_complete
from agentfit.interpretability.prompts import SYSTEM_PROMPT, build_user_prompt


@dataclass
class DimensionInterpretation:
    """LLM-generated interpretation for a single dimension."""
    summary: str = ""
    explanation: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "explanation": self.explanation,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


@dataclass
class OverallInterpretation:
    """LLM-generated interpretation for the overall evaluation."""
    summary: str = ""
    explanation: str = ""
    verdict: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "explanation": self.explanation,
            "verdict": self.verdict,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


@dataclass
class Recommendation:
    """Single actionable recommendation from the interpreter."""
    priority: str = "medium"
    area: str = ""
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority": self.priority,
            "area": self.area,
            "suggestion": self.suggestion,
        }


@dataclass
class InterpretationResult:
    """Complete interpretation output attached to an evaluation."""
    dimension_interpretations: Dict[str, DimensionInterpretation] = field(default_factory=dict)
    overall_interpretation: Optional[OverallInterpretation] = None
    recommendations: List[Recommendation] = field(default_factory=list)

    provider: str = ""
    model: str = ""
    interpretation_time_ms: float = 0.0
    raw_llm_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension_interpretations": {
                dim_id: interp.to_dict()
                for dim_id, interp in self.dimension_interpretations.items()
            },
            "overall_interpretation": (
                self.overall_interpretation.to_dict()
                if self.overall_interpretation
                else None
            ),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "meta": {
                "provider": self.provider,
                "model": self.model,
                "interpretation_time_ms": self.interpretation_time_ms,
            },
        }


class Interpreter:
    """
    LLM-powered evaluation interpreter.

    Takes a completed EvaluationResult (with scores, metrics, and
    behind-the-scenes calculation data), packages it alongside the
    BNP profile into a structured prompt, sends it to the configured
    LLM provider, and parses the response into typed interpretation
    objects.
    """

    def __init__(self, config: InterpretabilityConfig):
        config.validate()
        self.config = config

    async def interpret(
        self,
        result: EvaluationResult,
        bnp_profile: Optional[BNPProfile] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> InterpretationResult:
        """
        Generate LLM-powered interpretations for an evaluation result.

        Args:
            result: Completed evaluation with dimension scores and metrics.
            bnp_profile: The BNP that drove the evaluation (provides context).
            weights: Dimension weights used for aggregation.

        Returns:
            InterpretationResult with per-dimension and overall explanations.
        """
        start = time.time()

        user_prompt = build_user_prompt(result, bnp_profile, weights)

        logger.info(
            f"Requesting interpretation from {self.config.provider.value} "
            f"({self.config.get_model()})"
        )

        try:
            raw_response = await llm_complete(
                config=self.config,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.error(f"LLM interpretation call failed: {e}")
            return self._fallback_interpretation(result, str(e), start)

        interpretation = self._parse_response(raw_response, result)
        interpretation.provider = self.config.provider.value
        interpretation.model = self.config.get_model()
        interpretation.raw_llm_response = raw_response
        interpretation.interpretation_time_ms = (time.time() - start) * 1000

        logger.info(
            f"Interpretation completed in {interpretation.interpretation_time_ms:.0f}ms"
        )
        return interpretation

    def _parse_response(
        self, raw: str, result: EvaluationResult
    ) -> InterpretationResult:
        """Parse the LLM JSON response into typed objects."""
        interpretation = InterpretationResult()

        # Strip markdown fences if the model wrapped the JSON
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            last_fence = cleaned.rfind("```")
            cleaned = cleaned[first_newline + 1 : last_fence].strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM response was not valid JSON — using raw text as summary")
            interpretation.overall_interpretation = OverallInterpretation(
                summary=raw[:500],
                explanation=raw,
                verdict="Unable to parse structured response",
            )
            return interpretation

        # Dimension interpretations
        dim_interps = data.get("dimension_interpretations", {})
        for dim_id, dim_data in dim_interps.items():
            if dim_id in result.dimension_results:
                interpretation.dimension_interpretations[dim_id] = DimensionInterpretation(
                    summary=dim_data.get("summary", ""),
                    explanation=dim_data.get("explanation", ""),
                    strengths=dim_data.get("strengths", []),
                    weaknesses=dim_data.get("weaknesses", []),
                )

        # Overall interpretation
        overall = data.get("overall_interpretation", {})
        if overall:
            interpretation.overall_interpretation = OverallInterpretation(
                summary=overall.get("summary", ""),
                explanation=overall.get("explanation", ""),
                verdict=overall.get("verdict", ""),
                strengths=overall.get("strengths", []),
                weaknesses=overall.get("weaknesses", []),
            )

        # Recommendations
        for rec in data.get("recommendations", []):
            interpretation.recommendations.append(
                Recommendation(
                    priority=rec.get("priority", "medium"),
                    area=rec.get("area", ""),
                    suggestion=rec.get("suggestion", ""),
                )
            )

        return interpretation

    def _fallback_interpretation(
        self, result: EvaluationResult, error: str, start: float
    ) -> InterpretationResult:
        """Produce a minimal interpretation when the LLM call fails."""
        interpretation = InterpretationResult()
        interpretation.provider = self.config.provider.value
        interpretation.model = self.config.get_model()
        interpretation.interpretation_time_ms = (time.time() - start) * 1000

        interpretation.overall_interpretation = OverallInterpretation(
            summary=f"Interpretation unavailable due to LLM error: {error}",
            explanation=(
                f"The evaluation completed with an overall score of "
                f"{result.overall_score:.2f} ({result.overall_score * 100:.1f}%), "
                f"but the LLM interpretation could not be generated."
            ),
            verdict="PASSED" if result.passed else "FAILED",
        )
        return interpretation
