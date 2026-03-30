"""
Result Output Handler.

Serializes evaluation results to JSON/YAML formats with human-readable reporting.
Handles file writing with directory creation and formatting options.
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from agentfit.core.evaluator import EvaluationResult
from agentfit.bnp.schema import BNPProfile


class OutputFormatter:
    """Format and output evaluation results."""
    
    @staticmethod
    def result_to_dict(result: EvaluationResult, bnp_profile: Optional[BNPProfile] = None) -> Dict[str, Any]:
        """Convert evaluation result to dictionary for serialization.
        
        Args:
            result: EvaluationResult object
            bnp_profile: Optional BNP profile for context
            
        Returns:
            Dictionary representation of results
        """
        output = {
            "evaluation": {
                "id": result.id,
                "agent_id": result.agent_id,
                "scenario_id": result.scenario_id,
                "created_at": result.created_at,
                "completed_at": result.completed_at,
                "total_duration_ms": result.total_duration_ms,
                "overall_score": result.overall_score,
                "passed": result.passed,
            },
            "dimensions": {},
        }
        
        # Add dimension results
        for dim_id, dim_result in result.dimension_results.items():
            output["dimensions"][dim_id] = dim_result.to_dict()
        
        # Add BNP profile metadata if available
        if bnp_profile:
            output["profile"] = {
                "name": bnp_profile.name,
                "organization": bnp_profile.organization,
                "domain": bnp_profile.domain,
                "description": bnp_profile.description,
                "task_complexity": bnp_profile.task_complexity,
            }
        
        # Add interpretation if present
        if result.interpretation is not None:
            output["interpretation"] = result.interpretation.to_dict()
        
        return output
    
    @staticmethod
    def to_json(result: EvaluationResult, bnp_profile: Optional[BNPProfile] = None, indent: int = 2) -> str:
        """Convert result to JSON string.
        
        Args:
            result: EvaluationResult object
            bnp_profile: Optional BNP profile
            indent: JSON indentation level
            
        Returns:
            JSON string
        """
        data = OutputFormatter.result_to_dict(result, bnp_profile)
        return json.dumps(data, indent=indent, default=str)
    
    @staticmethod
    def to_yaml(result: EvaluationResult, bnp_profile: Optional[BNPProfile] = None) -> str:
        """Convert result to YAML string.
        
        Args:
            result: EvaluationResult object
            bnp_profile: Optional BNP profile
            
        Returns:
            YAML string
        """
        data = OutputFormatter.result_to_dict(result, bnp_profile)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def write_to_file(
        result: EvaluationResult,
        output_path: str,
        format: str = "json",
        bnp_profile: Optional[BNPProfile] = None
    ) -> Path:
        """Write evaluation results to file.
        
        Args:
            result: EvaluationResult object
            output_path: Path to write results to
            format: Output format (json or yaml)
            bnp_profile: Optional BNP profile
            
        Returns:
            Path object of written file
            
        Raises:
            ValueError: If format is not supported
            IOError: If file writing fails
        """
        output_path = Path(output_path)
        
        # Create directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine format
        format = format.lower().strip()
        if format not in ["json", "yaml", "yml"]:
            raise ValueError(f"Unsupported format: {format}. Choose 'json' or 'yaml'")
        
        # Serialize based on format
        if format == "json":
            content = OutputFormatter.to_json(result, bnp_profile)
        else:  # yaml or yml
            content = OutputFormatter.to_yaml(result, bnp_profile)
        
        # Write to file
        output_path.write_text(content)
        
        return output_path


class ReportGenerator:
    """Generate human-readable evaluation reports."""
    
    @staticmethod
    def generate_summary(result: EvaluationResult, bnp_profile: Optional[BNPProfile] = None) -> str:
        """Generate a human-readable summary of evaluation results.
        
        Args:
            result: EvaluationResult object
            bnp_profile: Optional BNP profile
            
        Returns:
            Formatted summary string
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("AGENTFIT EVALUATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Metadata
        lines.append("EVALUATION METADATA")
        lines.append("-" * 40)
        lines.append(f"Evaluation ID: {result.id}")
        lines.append(f"Agent ID: {result.agent_id}")
        lines.append(f"Scenario ID: {result.scenario_id}")
        lines.append(f"Created: {result.created_at}")
        if result.completed_at:
            lines.append(f"Completed: {result.completed_at}")
        lines.append(f"Duration: {result.total_duration_ms:.2f}ms")
        lines.append("")
        
        # Profile information
        if bnp_profile:
            lines.append("PROFILE INFORMATION")
            lines.append("-" * 40)
            lines.append(f"Name: {bnp_profile.name}")
            lines.append(f"Organization: {bnp_profile.organization}")
            lines.append(f"Domain: {bnp_profile.domain}")
            lines.append(f"Description: {bnp_profile.description}")
            lines.append(f"Task Complexity: {bnp_profile.task_complexity}")
            lines.append("")
        
        # Overall results
        lines.append("OVERALL RESULTS")
        lines.append("-" * 40)
        lines.append(f"Overall Score: {result.overall_score:.2f} / 1.0 ({result.overall_score*100:.1f}%)")
        lines.append(f"Status: {'PASSED' if result.passed else 'FAILED'}")
        lines.append("")
        
        # Dimension results
        lines.append("DIMENSION RESULTS")
        lines.append("-" * 40)

        # Pre-fetch interpretation data if available
        dim_interps = {}
        if result.interpretation and result.interpretation.dimension_interpretations:
            dim_interps = result.interpretation.dimension_interpretations

        for dim_id, dim_result in result.dimension_results.items():
            percentage = dim_result.get_percentage()
            status = "✓" if dim_result.passed else "✗"
            lines.append(f"{status} {dim_result.dimension_name} ({dim_id})")
            lines.append(f"  Score: {dim_result.score:.2f} / {dim_result.max_score} ({percentage:.1f}%)")
            lines.append(f"  Scoring Method: {dim_result.scoring_method.value}")
            lines.append(f"  Duration: {dim_result.execution_time_ms:.2f}ms")
            
            if dim_result.feedback:
                lines.append(f"  Feedback: {dim_result.feedback}")
            
            if dim_result.error:
                lines.append(f"  Error: {dim_result.error}")
            
            if dim_result.metrics:
                lines.append("  Metrics:")
                for metric in dim_result.metrics:
                    metric_pct = metric.to_percentage()
                    lines.append(f"    - {metric.name}: {metric.value}/{metric.max_value} ({metric_pct:.1f}%)")

            # Inline interpretation for this dimension
            if dim_id in dim_interps:
                interp = dim_interps[dim_id]
                lines.append(f"  Interpretation: {interp.summary}")
                if interp.explanation:
                    for line in interp.explanation.split(". "):
                        line = line.strip()
                        if line:
                            lines.append(f"    {line}.")
                if interp.strengths:
                    lines.append("  Strengths:")
                    for s in interp.strengths:
                        lines.append(f"    + {s}")
                if interp.weaknesses:
                    lines.append("  Weaknesses:")
                    for w in interp.weaknesses:
                        lines.append(f"    - {w}")
            
            lines.append("")
        
        # Overall interpretation section
        if result.interpretation and result.interpretation.overall_interpretation:
            overall = result.interpretation.overall_interpretation
            lines.append("OVERALL INTERPRETATION")
            lines.append("-" * 40)
            lines.append(f"Summary: {overall.summary}")
            if overall.explanation:
                lines.append(f"Analysis: {overall.explanation}")
            lines.append(f"Verdict: {overall.verdict}")
            if overall.strengths:
                lines.append("Strengths:")
                for s in overall.strengths:
                    lines.append(f"  + {s}")
            if overall.weaknesses:
                lines.append("Weaknesses:")
                for w in overall.weaknesses:
                    lines.append(f"  - {w}")
            lines.append("")

        # Recommendations section
        if result.interpretation and result.interpretation.recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 40)
            for i, rec in enumerate(result.interpretation.recommendations, 1):
                priority_tag = f"[{rec.priority.upper()}]"
                lines.append(f"  {i}. {priority_tag} {rec.area}")
                lines.append(f"     {rec.suggestion}")
            lines.append("")

        # Footer
        lines.append("=" * 80)
        lines.append(f"Report generated: {datetime.utcnow().isoformat()}")
        if result.interpretation:
            lines.append(
                f"Interpretation by: {result.interpretation.provider} "
                f"({result.interpretation.model}) in "
                f"{result.interpretation.interpretation_time_ms:.0f}ms"
            )
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def print_summary(result: EvaluationResult, bnp_profile: Optional[BNPProfile] = None) -> None:
        """Print evaluation summary to stdout.
        
        Args:
            result: EvaluationResult object
            bnp_profile: Optional BNP profile
        """
        print(ReportGenerator.generate_summary(result, bnp_profile))
