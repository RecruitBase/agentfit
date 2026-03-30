"""Tests for the evaluator."""
import pytest
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest, EvaluationResult
from agentfit.bnp.schema import BNPProfile, AgentRequirement
from agentfit.protocol import UniversalAgentProtocol, Message, MessageRole


class TestEvaluationRequest:
    """Test evaluation request."""

    def test_evaluation_request_creation(self):
        """Test creating evaluation request."""
        req = EvaluationRequest(
            agent_id="test-agent",
            bnp_profile=None,
            dimensions=["task_competence", "tool_use"]
        )
        assert req.agent_id == "test-agent"
        assert "task_competence" in req.dimensions


class TestEvaluationResult:
    """Test evaluation result."""

    def test_evaluation_result_creation(self):
        """Test creating evaluation result."""
        result = EvaluationResult(
            agent_id="test-agent",
            overall_score=0.85,
            dimension_scores={"task_competence": 0.9, "tool_use": 0.8}
        )
        assert result.agent_id == "test-agent"
        assert result.overall_score == 0.85
        assert result.dimension_scores["task_competence"] == 0.9


class TestEvaluator:
    """Test the evaluator."""

    def test_evaluator_initialization(self):
        """Test initializing evaluator."""
        evaluator = Evaluator()
        assert evaluator is not None
        assert hasattr(evaluator, 'evaluate')

    @pytest.mark.asyncio
    async def test_evaluator_basic_evaluation(self):
        """Test basic evaluation."""
        evaluator = Evaluator()
        
        # Create a minimal protocol instance
        protocol = UniversalAgentProtocol()
        
        request = EvaluationRequest(
            agent_id="test-agent",
            dimensions=["task_competence"]
        )
        
        # This will test if evaluation runs without errors
        result = await evaluator.evaluate(request)
        assert result is not None
        assert result.agent_id == "test-agent"

    def test_evaluator_with_sync_wrapper(self):
        """Test evaluator with sync wrapper."""
        evaluator = Evaluator()
        request = EvaluationRequest(
            agent_id="test-agent",
            dimensions=["task_competence"]
        )
        
        # Run async evaluation
        result = asyncio.run(evaluator.evaluate(request))
        assert result is not None
        assert result.agent_id == "test-agent"


class TestEvaluatorDimensionFiltering:
    """Test dimension filtering in evaluator."""

    def test_all_dimensions_evaluation(self):
        """Test evaluating all dimensions."""
        evaluator = Evaluator()
        request = EvaluationRequest(
            agent_id="test-agent",
            dimensions=None  # All dimensions
        )
        
        result = asyncio.run(evaluator.evaluate(request))
        # Should have scores for all 7 dimensions
        assert len(result.dimension_scores) >= 5

    def test_specific_dimensions_evaluation(self):
        """Test evaluating specific dimensions."""
        evaluator = Evaluator()
        request = EvaluationRequest(
            agent_id="test-agent",
            dimensions=["task_competence", "tool_use"]
        )
        
        result = asyncio.run(evaluator.evaluate(request))
        assert "task_competence" in result.dimension_scores
        assert "tool_use" in result.dimension_scores


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
