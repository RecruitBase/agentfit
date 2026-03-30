"""Tests for BNP (Business Need Profile)."""
import pytest
from pathlib import Path
from agentfit.bnp.parser import BNPParser
from agentfit.bnp.schema import BNPProfile, AgentRequirement, Domain


class TestBNPParser:
    """Test BNP parser."""

    def test_parser_initialization(self):
        """Test initializing parser."""
        parser = BNPParser()
        assert parser is not None

    def test_parse_minimal_bnp(self):
        """Test parsing minimal BNP."""
        bnp_content = """
# Business Need Profile

## Organization Info
- Name: Test Corp
- Industry: Technology

## Agent Requirements
- Domain: customer_service
- Criticality: medium
"""
        profile = BNPParser.parse(bnp_content)
        assert profile is not None
        assert profile.organization_name == "Test Corp"

    def test_parse_full_bnp(self):
        """Test parsing full BNP."""
        bnp_content = """
# Business Need Profile

## Organization Info
- Name: Test Corp
- Industry: Finance

## Agent Requirements
- Domain: data_analysis
- Criticality: high
- Autonomy Level: semi-autonomous
- Required Dimensions:
  - task_competence
  - safety_alignment
  - compliance_auditability

## Tool Requirements
- Required Tools:
  - database_query
  - reporting

## Performance Requirements
- Max Latency: 5s
- Min Throughput: 100 req/s
"""
        profile = BNPParser.parse(bnp_content)
        assert profile is not None
        assert "task_competence" in profile.required_dimensions


class TestBNPProfile:
    """Test BNP profile."""

    def test_profile_creation(self):
        """Test creating profile."""
        profile = BNPProfile(
            organization_name="Test Org",
            industry="Tech",
            agent_domain=Domain.GENERAL
        )
        assert profile.organization_name == "Test Org"
        assert profile.industry == "Tech"

    def test_profile_validation(self):
        """Test profile validation."""
        profile = BNPProfile(
            organization_name="Test",
            industry="Tech",
            agent_domain=Domain.GENERAL
        )
        # Should not raise
        assert profile is not None


class TestAgentRequirement:
    """Test agent requirement."""

    def test_requirement_creation(self):
        """Test creating requirement."""
        req = AgentRequirement(
            name="search_capability",
            description="Agent must search the web",
            criticality="high"
        )
        assert req.name == "search_capability"
        assert req.criticality == "high"


class TestBNPIntegration:
    """Test BNP integration with evaluation."""

    def test_bnp_with_evaluation_request(self):
        """Test using BNP with evaluation."""
        profile = BNPProfile(
            organization_name="Test",
            industry="Tech",
            agent_domain=Domain.CUSTOMER_SERVICE,
            required_dimensions=["task_competence", "tool_use"]
        )
        
        assert profile.required_dimensions is not None
        assert len(profile.required_dimensions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
