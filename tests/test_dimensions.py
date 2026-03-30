"""Tests for evaluation dimensions."""
import pytest
from agentfit.core.dimension import DimensionResult, DimensionRegistry
from agentfit.dimensions.task_competence import TaskCompetence
from agentfit.dimensions.tool_use import ToolUse
from agentfit.dimensions.autonomy_escalation import AutonomyEscalation
from agentfit.dimensions.safety_alignment import SafetyAlignment
from agentfit.dimensions.compliance_auditability import ComplianceAuditability
from agentfit.dimensions.operational_performance import OperationalPerformance
from agentfit.dimensions.deployment_compatibility import DeploymentCompatibility


class TestDimensionRegistry:
    """Test dimension registry."""

    def test_register_dimension(self):
        """Test registering a dimension."""
        registry = DimensionRegistry()
        registry.register(TaskCompetence)
        assert "task_competence" in registry._registry

    def test_get_dimension(self):
        """Test getting a dimension."""
        registry = DimensionRegistry()
        registry.register(TaskCompetence)
        dim = registry.get("task_competence")
        assert dim == TaskCompetence

    def test_list_dimensions(self):
        """Test listing all dimensions."""
        registry = DimensionRegistry()
        registry.register(TaskCompetence)
        registry.register(ToolUse)
        dims = registry.list()
        assert "task_competence" in dims
        assert "tool_use" in dims

    def test_get_all_dimensions(self):
        """Test getting all registered dimensions."""
        registry = DimensionRegistry()
        registry.register(TaskCompetence)
        registry.register(ToolUse)
        all_dims = registry.get_all()
        assert len(all_dims) == 2


class TestDimensionResult:
    """Test dimension result."""

    def test_dimension_result_creation(self):
        """Test creating dimension result."""
        result = DimensionResult(
            dimension_name="task_competence",
            score=0.85,
            details={"task_understanding": 0.9, "execution": 0.8}
        )
        assert result.dimension_name == "task_competence"
        assert result.score == 0.85
        assert result.details["task_understanding"] == 0.9

    def test_dimension_result_validation(self):
        """Test score validation."""
        # Valid score
        result = DimensionResult(
            dimension_name="test",
            score=0.75,
            details={}
        )
        assert result.score == 0.75

        # Invalid score (out of range)
        with pytest.raises(ValueError):
            DimensionResult(
                dimension_name="test",
                score=1.5,  # Greater than 1.0
                details={}
            )


class TestTaskCompetenceDimension:
    """Test task competence dimension."""

    def test_task_competence_initialization(self):
        """Test initializing task competence dimension."""
        dim = TaskCompetence()
        assert dim.name == "task_competence"
        assert dim.description is not None
        assert dim.weight == 0.15

    def test_task_competence_sub_metrics(self):
        """Test task competence sub-metrics."""
        dim = TaskCompetence()
        metrics = dim.get_sub_metrics()
        assert "task_understanding" in metrics
        assert "planning" in metrics
        assert "execution" in metrics


class TestToolUseDimension:
    """Test tool use dimension."""

    def test_tool_use_initialization(self):
        """Test initializing tool use dimension."""
        dim = ToolUse()
        assert dim.name == "tool_use"
        assert dim.weight == 0.15

    def test_tool_use_metrics(self):
        """Test tool use metrics."""
        dim = ToolUse()
        metrics = dim.get_sub_metrics()
        assert "tool_selection" in metrics
        assert "tool_invocation" in metrics


class TestAllDimensions:
    """Test all dimensions are properly implemented."""

    def test_autonomy_dimension(self):
        """Test autonomy & escalation dimension."""
        dim = AutonomyEscalation()
        assert dim.name == "autonomy_escalation"
        assert 0 <= dim.weight <= 1

    def test_safety_dimension(self):
        """Test safety & alignment dimension."""
        dim = SafetyAlignment()
        assert dim.name == "safety_alignment"
        assert 0 <= dim.weight <= 1

    def test_compliance_dimension(self):
        """Test compliance & auditability dimension."""
        dim = ComplianceAuditability()
        assert dim.name == "compliance_auditability"
        assert 0 <= dim.weight <= 1

    def test_operational_dimension(self):
        """Test operational performance dimension."""
        dim = OperationalPerformance()
        assert dim.name == "operational_performance"
        assert 0 <= dim.weight <= 1

    def test_deployment_dimension(self):
        """Test deployment compatibility dimension."""
        dim = DeploymentCompatibility()
        assert dim.name == "deployment_compatibility"
        assert 0 <= dim.weight <= 1

    def test_all_weights_sum_to_one(self):
        """Test that all dimension weights sum to approximately 1.0."""
        dimensions = [
            TaskCompetence(),
            ToolUse(),
            AutonomyEscalation(),
            SafetyAlignment(),
            ComplianceAuditability(),
            OperationalPerformance(),
            DeploymentCompatibility(),
        ]
        total_weight = sum(dim.weight for dim in dimensions)
        assert 0.99 <= total_weight <= 1.01  # Allow small floating point errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
