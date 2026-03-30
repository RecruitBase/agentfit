"""
Prompt Templates for Interpretation.

Constructs the system and user prompts sent to the LLM, embedding the
full evaluation context: BNP profile, per-dimension scores with sub-metric
breakdowns, weights, and the overall aggregation arithmetic.
"""

from typing import Any, Dict, List, Optional
import json

from agentfit.core.evaluator import EvaluationResult
from agentfit.bnp.schema import BNPProfile


SYSTEM_PROMPT = """\
You are an expert AI agent evaluation analyst working within the AgentFit \
framework. Your role is to interpret raw evaluation scores and provide \
clear, actionable explanations that help stakeholders understand WHY an \
agent scored the way it did — not just WHAT the numbers are.

Guidelines:
- Ground every explanation in the Business Need Profile (BNP) context. \
  Explain scores relative to what the organization actually needs.
- Reference specific sub-metrics and calculation details when explaining \
  a dimension score (e.g. "task_success contributed 40% of the dimension \
  score and the agent achieved 1.0/1.0 here, but step_coverage at 60% \
  dragged the overall dimension score down").
- Be concrete and specific — avoid vague statements like "the agent did \
  okay". Instead say "the agent completed the primary task but missed 2 \
  of 5 expected workflow steps, specifically …".
- When the BNP has weighted dimensions, explain how the weights affected \
  the overall score (e.g. "task_competence carries 35% weight and scored \
  0.82, contributing 0.287 to the overall 0.74").
- Provide actionable recommendations tied to the weakest areas.

You MUST respond with valid JSON matching this exact schema (no markdown \
fences, no extra keys):

{
  "dimension_interpretations": {
    "<dimension_id>": {
      "summary": "1-2 sentence plain-english summary of this score",
      "explanation": "Detailed explanation referencing sub-metrics, weights, \
and BNP requirements. 3-5 sentences.",
      "strengths": ["strength 1", "..."],
      "weaknesses": ["weakness 1", "..."]
    }
  },
  "overall_interpretation": {
    "summary": "1-2 sentence overall assessment",
    "explanation": "Detailed explanation of how the overall score was \
computed from dimension scores and weights. Reference specific numbers.",
    "verdict": "PASSED or FAILED with reasoning tied to BNP thresholds",
    "strengths": ["strength 1", "..."],
    "weaknesses": ["weakness 1", "..."]
  },
  "recommendations": [
    {
      "priority": "high | medium | low",
      "area": "dimension or capability area",
      "suggestion": "Specific, actionable recommendation"
    }
  ]
}"""


def build_user_prompt(
    result: EvaluationResult,
    bnp_profile: Optional[BNPProfile],
    weights: Optional[Dict[str, float]],
) -> str:
    """
    Build the user-facing prompt containing all evaluation data.

    Includes raw scores, sub-metric breakdowns, weight arithmetic,
    and the full BNP profile context so the LLM can produce grounded
    interpretations.
    """
    sections: List[str] = []

    # ── BNP Profile Context ──────────────────────────────────────────
    if bnp_profile:
        bnp_section = _build_bnp_section(bnp_profile)
        sections.append(bnp_section)

    # ── Per-Dimension Raw Data ───────────────────────────────────────
    sections.append(_build_dimensions_section(result, weights))

    # ── Overall Score Arithmetic ─────────────────────────────────────
    sections.append(_build_overall_section(result, weights))

    sections.append(
        "Based on all of the above, provide your JSON interpretation."
    )

    return "\n\n".join(sections)


def _build_bnp_section(bnp: BNPProfile) -> str:
    lines = ["=== BUSINESS NEED PROFILE (BNP) ==="]
    lines.append(f"Name: {bnp.name}")
    lines.append(f"Organization: {bnp.organization}")
    lines.append(f"Domain: {bnp.domain}")
    lines.append(f"Description: {bnp.description}")
    lines.append(f"Task Complexity: {bnp.task_complexity}")

    if bnp.requirements:
        lines.append("\nRequirements:")
        for req in bnp.requirements:
            flag = "[REQUIRED]" if req.required else "[OPTIONAL]"
            rate = f" (min success rate: {req.min_success_rate})" if req.min_success_rate else ""
            lines.append(f"  - {flag} {req.capability}: {req.description}{rate}")

    if bnp.evaluation_dimensions:
        lines.append("\nDimension Weights:")
        for dw in bnp.evaluation_dimensions:
            lines.append(f"  - {dw.dimension}: weight={dw.weight}")

    if bnp.compliance_requirements:
        lines.append(f"\nCompliance: {', '.join(bnp.compliance_requirements)}")

    if bnp.max_latency_ms:
        lines.append(f"Max Latency: {bnp.max_latency_ms}ms")

    return "\n".join(lines)


def _build_dimensions_section(
    result: EvaluationResult,
    weights: Optional[Dict[str, float]],
) -> str:
    lines = ["=== PER-DIMENSION EVALUATION DATA ==="]

    for dim_id, dim_result in result.dimension_results.items():
        w = weights.get(dim_id, 0.0) if weights else None
        pct = dim_result.get_percentage()
        weight_str = f" | weight={w:.3f}" if w is not None else ""
        contribution = f" | contribution_to_overall={dim_result.score * w:.4f}" if w else ""

        lines.append(f"\n--- {dim_result.dimension_name} ({dim_id}) ---")
        lines.append(f"Score: {dim_result.score:.4f} / {dim_result.max_score} ({pct:.1f}%){weight_str}{contribution}")
        lines.append(f"Passed: {dim_result.passed}")
        lines.append(f"Scoring Method: {dim_result.scoring_method.value}")

        if dim_result.feedback:
            lines.append(f"Feedback: {dim_result.feedback}")

        if dim_result.metrics:
            lines.append("Sub-Metrics Breakdown:")
            for m in dim_result.metrics:
                m_pct = m.to_percentage()
                w_info = ""
                if "weight" in m.metadata:
                    w_info = f" (weight in dimension: {m.metadata['weight']})"
                lines.append(
                    f"  - {m.name}: {m.value:.4f}/{m.max_value} ({m_pct:.1f}%){w_info}"
                )
            lines.append("Calculation: weighted_sum = " + " + ".join(
                f"{m.value:.4f}*{m.metadata.get('weight', '?')}"
                for m in dim_result.metrics
                if "weight" in m.metadata
            ))

        if dim_result.error:
            lines.append(f"Error: {dim_result.error}")

        if dim_result.metadata:
            safe_meta = _safe_metadata(dim_result.metadata)
            if safe_meta:
                lines.append(f"Metadata: {json.dumps(safe_meta, default=str)}")

    return "\n".join(lines)


def _build_overall_section(
    result: EvaluationResult,
    weights: Optional[Dict[str, float]],
) -> str:
    lines = ["=== OVERALL SCORE COMPUTATION ==="]
    lines.append(f"Overall Score: {result.overall_score:.4f} ({result.overall_score * 100:.1f}%)")
    lines.append(f"Passed: {result.passed}")

    if weights:
        lines.append("\nWeighted Aggregation:")
        running_total = 0.0
        for dim_id, dim_result in result.dimension_results.items():
            w = weights.get(dim_id, 0.0)
            contrib = dim_result.score * w
            running_total += contrib
            lines.append(
                f"  {dim_id}: {dim_result.score:.4f} * {w:.3f} = {contrib:.4f}"
            )
        total_weight = sum(weights.get(d, 0.0) for d in result.dimension_results)
        lines.append(f"  Sum of contributions: {running_total:.4f}")
        lines.append(f"  Sum of weights: {total_weight:.4f}")
        lines.append(f"  Overall = {running_total:.4f} / {total_weight:.4f} = {result.overall_score:.4f}")
    else:
        lines.append("Aggregation: equal-weight average across all dimensions")

    lines.append(f"\nPass threshold: 0.7 (70%)")
    lines.append(f"Duration: {result.total_duration_ms:.2f}ms")

    return "\n".join(lines)


def _safe_metadata(meta: Dict[str, Any], max_depth: int = 2) -> Dict[str, Any]:
    """Flatten metadata to JSON-safe types, limiting depth to keep prompts compact."""
    safe: Dict[str, Any] = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            safe[k] = v
        elif isinstance(v, dict) and max_depth > 0:
            safe[k] = _safe_metadata(v, max_depth - 1)
        elif isinstance(v, (list, tuple)):
            safe[k] = [str(i) for i in v[:10]]
        else:
            safe[k] = str(v)[:200]
    return safe
