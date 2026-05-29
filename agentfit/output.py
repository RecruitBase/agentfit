"""
Result Output Handler.

Serializes evaluation results to JSON/YAML and produces governance-first
human-readable reports.

Report hierarchy (research-grounded):
  1. GOVERNANCE DECISION  — headline binary: PASS / FAIL + which dims failed
  2. RELIABILITY          — Pass@k / Pass^k when k_trials > 1
  3. DIMENSION THRESHOLDS — per-dimension threshold vs actual score
  4. SUB-METRIC EVIDENCE  — continuous scores as supporting evidence
  5. FAILURE MODES        — structured per-trial failure records
  6. INTERPRETATION       — LLM-grounded narrative (when enabled)
  7. HARNESS SNAPSHOT     — versioned eval environment for audit trail
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from agentfit.core.evaluator import EvaluationResult
from agentfit.bnp.schema import BNPProfile


class OutputFormatter:
    """Format and output evaluation results."""

    @staticmethod
    def result_to_dict(
        result: EvaluationResult,
        bnp_profile: Optional[BNPProfile] = None,
    ) -> Dict[str, Any]:
        output: Dict[str, Any] = {
            # ── Governance decision (headline) ────────────────────────────
            "governance": result.governance.to_dict() if result.governance else None,
            # ── Evaluation metadata ───────────────────────────────────────
            "evaluation": {
                "id": result.id,
                "agent_id": result.agent_id,
                "scenario_id": result.scenario_id,
                "created_at": result.created_at,
                "completed_at": result.completed_at,
                "total_duration_ms": result.total_duration_ms,
                # Continuous score kept as supporting evidence, not headline
                "overall_score": result.overall_score,
                "passed": result.passed,
            },
            # ── Reliability (populated when k_trials > 1) ─────────────────
            "reliability": {k: v.to_dict() for k, v in result.reliability.items()},
            # ── Per-dimension results (sub-metric evidence) ────────────────
            "dimensions": {
                k: v.to_dict() for k, v in result.dimension_results.items()
            },
            # ── Failure modes ─────────────────────────────────────────────
            "failure_modes": [f.to_dict() for f in result.failure_modes],
            # ── Harness snapshot ──────────────────────────────────────────
            "harness": result.harness_snapshot.to_dict() if result.harness_snapshot else None,
        }

        if bnp_profile:
            output["profile"] = {
                "name": bnp_profile.name,
                "organization": bnp_profile.organization,
                "domain": bnp_profile.domain,
                "description": bnp_profile.description,
                "task_complexity": bnp_profile.task_complexity,
                "k_trials": bnp_profile.k_trials,
            }

        if result.interpretation is not None:
            output["interpretation"] = result.interpretation.to_dict()

        return output

    @staticmethod
    def to_json(
        result: EvaluationResult,
        bnp_profile: Optional[BNPProfile] = None,
        indent: int = 2,
    ) -> str:
        return json.dumps(
            OutputFormatter.result_to_dict(result, bnp_profile),
            indent=indent,
            default=str,
        )

    @staticmethod
    def to_yaml(
        result: EvaluationResult,
        bnp_profile: Optional[BNPProfile] = None,
    ) -> str:
        return yaml.dump(
            OutputFormatter.result_to_dict(result, bnp_profile),
            default_flow_style=False,
            sort_keys=False,
        )

    @staticmethod
    def write_to_file(
        result: EvaluationResult,
        output_path: str,
        format: str = "json",
        bnp_profile: Optional[BNPProfile] = None,
    ) -> Path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fmt = format.lower().strip()
        if fmt not in ("json", "yaml", "yml"):
            raise ValueError(f"Unsupported format: {fmt}. Choose 'json' or 'yaml'")
        content = (
            OutputFormatter.to_json(result, bnp_profile)
            if fmt == "json"
            else OutputFormatter.to_yaml(result, bnp_profile)
        )
        p.write_text(content)
        return p


class ReportGenerator:
    """Produce governance-first human-readable evaluation reports."""

    @staticmethod
    def generate_summary(
        result: EvaluationResult,
        bnp_profile: Optional[BNPProfile] = None,
    ) -> str:
        lines: list[str] = []
        W = 80

        def rule(char="="):
            lines.append(char * W)

        def section(title: str):
            lines.append("")
            lines.append(title)
            lines.append("-" * 40)

        rule()
        lines.append("AGENTFIT EVALUATION REPORT")
        rule()

        # ── 1. GOVERNANCE DECISION (headline) ─────────────────────────────
        gov = result.governance
        if gov:
            lines.append("")
            if gov.passed:
                lines.append("  GOVERNANCE DECISION:  ✓ PASS")
            else:
                lines.append("  GOVERNANCE DECISION:  ✗ FAIL")
            lines.append(f"  {gov.rationale}")

            if gov.regression_failures:
                lines.append(
                    f"  ⚠  REGRESSION ALERT: {', '.join(gov.regression_failures)}"
                )
        else:
            lines.append("")
            lines.append(f"  STATUS: {'✓ PASSED' if result.passed else '✗ FAILED'}")

        # ── 2. RELIABILITY (only when k > 1) ──────────────────────────────
        if result.reliability:
            section("RELIABILITY")
            k_val = next(iter(result.reliability.values())).k
            lines.append(f"  Trials run: {k_val}")
            lines.append(
                f"  {'Dimension':<35} {'Pass@k':<12} {'Pass^k':<12} {'σ':<8}"
            )
            lines.append("  " + "-" * 68)
            for dim_id, rel in result.reliability.items():
                rel_mode = "pass_all_k"
                if bnp_profile:
                    rel_mode = bnp_profile.get_dimension_reliability_modes().get(
                        dim_id, "pass_at_k"
                    )
                binding = rel.reliability_label(rel_mode)
                lines.append(
                    f"  {dim_id:<35} "
                    f"{'PASS' if rel.pass_at_k == 1.0 else 'FAIL':<12} "
                    f"{'PASS' if rel.pass_all_k == 1.0 else 'FAIL':<12} "
                    f"{rel.dispersion:<8.3f}"
                    f"  [binding: {binding}]"
                )

        # ── 3. THRESHOLD RESULTS ───────────────────────────────────────────
        if gov and gov.threshold_results:
            section("DIMENSION THRESHOLDS")
            lines.append(
                f"  {'Dimension':<35} {'Score':<8} {'Threshold':<12} {'Status':<8} {'Lifecycle'}"
            )
            lines.append("  " + "-" * 72)
            for dim_id, tr in gov.threshold_results.items():
                status = "✓ PASS" if tr.met else "✗ FAIL"
                lifecycle_tag = " ⚠ REGRESSION" if tr.is_regression_failure else ""
                lines.append(
                    f"  {dim_id:<35} {tr.score:<8.2f} {tr.threshold:<12.2f} "
                    f"{status:<8} {tr.lifecycle}{lifecycle_tag}"
                )

        # ── 4. SUB-METRIC EVIDENCE ─────────────────────────────────────────
        section("SUB-METRIC EVIDENCE")
        dim_interps = {}
        if result.interpretation and result.interpretation.dimension_interpretations:
            dim_interps = result.interpretation.dimension_interpretations

        for dim_id, dr in result.dimension_results.items():
            status = "✓" if dr.passed else "✗"
            lines.append(f"  {status} {dr.dimension_name} ({dim_id})")
            lines.append(
                f"    Score: {dr.score:.2f} / {dr.max_score}  "
                f"({dr.get_percentage():.1f}%)  "
                f"[{dr.scoring_method.value}]  "
                f"{dr.execution_time_ms:.1f}ms"
            )
            if dr.feedback:
                lines.append(f"    Feedback: {dr.feedback}")
            if dr.metrics:
                for m in dr.metrics:
                    weight = m.metadata.get("weight", "")
                    w_str = f"  weight={weight}" if weight else ""
                    lines.append(
                        f"      {m.name:<30} {m.value:.3f}/{m.max_value}{w_str}"
                    )
            if dim_id in dim_interps:
                interp = dim_interps[dim_id]
                lines.append(f"    Interpretation: {interp.summary}")
                if interp.strengths:
                    for s in interp.strengths:
                        lines.append(f"      + {s}")
                if interp.weaknesses:
                    for w in interp.weaknesses:
                        lines.append(f"      - {w}")
            lines.append("")

        # ── 5. FAILURE MODES ───────────────────────────────────────────────
        if result.failure_modes:
            section("FAILURE MODES")
            lines.append(
                f"  {len(result.failure_modes)} failure(s) recorded across trials."
            )
            for fm in result.failure_modes[:10]:  # cap at 10 in report
                lines.append(
                    f"  [{fm.severity.upper()}] trial {fm.trial_num} "
                    f"/ {fm.dimension}: {fm.description[:80]}"
                )
            if len(result.failure_modes) > 10:
                lines.append(
                    f"  … and {len(result.failure_modes) - 10} more "
                    "(see full JSON output)"
                )

        # ── 6. INTERPRETATION ──────────────────────────────────────────────
        if result.interpretation:
            interp = result.interpretation
            if interp.overall_interpretation:
                section("OVERALL INTERPRETATION")
                oi = interp.overall_interpretation
                lines.append(f"  {oi.summary}")
                if oi.explanation:
                    lines.append(f"  {oi.explanation}")
                lines.append(f"  Verdict: {oi.verdict}")
                if oi.strengths:
                    for s in oi.strengths:
                        lines.append(f"    + {s}")
                if oi.weaknesses:
                    for w in oi.weaknesses:
                        lines.append(f"    - {w}")

            if interp.recommendations:
                section("RECOMMENDATIONS")
                for i, rec in enumerate(interp.recommendations, 1):
                    lines.append(f"  {i}. [{rec.priority.upper()}] {rec.area}")
                    lines.append(f"     {rec.suggestion}")

        # ── 7. HARNESS SNAPSHOT ────────────────────────────────────────────
        if result.harness_snapshot:
            hs = result.harness_snapshot
            section("HARNESS SNAPSHOT  (audit trail)")
            lines.append(f"  Agent:     {hs.agent_id}  [{hs.agent_framework}]")
            if hs.model:
                lines.append(f"  Model:     {hs.model}")
            if hs.temperature is not None:
                lines.append(f"  Temp:      {hs.temperature}")
            lines.append(f"  K trials:  {hs.k_trials}")
            lines.append(f"  Scenario:  {hs.scenario_id}")
            lines.append(f"  Captured:  {hs.captured_at}")
            lines.append(f"  AgentFit:  v{hs.agentfit_version}")

        # ── Footer ────────────────────────────────────────────────────────
        lines.append("")
        rule()
        lines.append(
            f"Report generated: {datetime.now(timezone.utc).isoformat()}"
        )
        if result.interpretation:
            i = result.interpretation
            lines.append(
                f"Interpretation: {i.provider} ({i.model}) "
                f"in {i.interpretation_time_ms:.0f}ms"
            )
        lines.append(
            f"Supporting score: {result.overall_score:.2f} / 1.0  "
            "(use governance decision, not this float, for deploy/block)"
        )
        rule()

        return "\n".join(lines)

    @staticmethod
    def print_summary(
        result: EvaluationResult,
        bnp_profile: Optional[BNPProfile] = None,
    ) -> None:
        print(ReportGenerator.generate_summary(result, bnp_profile))
