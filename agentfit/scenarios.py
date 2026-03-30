"""
Scenario and Test Data System.

Provides default test scenarios for each dimension and domain.
Enables parameterization of evaluation tasks based on complexity and domain.
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from agentfit.bnp.schema import TaskComplexity, AgentDomain


class ScenarioTemplate:
    """Default scenario templates by domain and complexity."""
    
    # Customer Service domain scenarios
    CUSTOMER_SERVICE_SIMPLE = {
        "id": "cs-simple-001",
        "domain": "customer_service",
        "complexity": "simple",
        "task": "Help a customer find information about their account balance.",
        "expected_steps": [
            "Understand the customer's request",
            "Retrieve account information",
            "Present the balance",
        ],
        "expected_tools": ["account_lookup", "data_fetch"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 5,
            "required_info": ["balance"]
        }
    }
    
    CUSTOMER_SERVICE_MODERATE = {
        "id": "cs-moderate-001",
        "domain": "customer_service",
        "complexity": "moderate",
        "task": "Resolve a customer complaint about a billing error and process a refund.",
        "expected_steps": [
            "Listen to the customer's issue",
            "Verify the billing details",
            "Identify the billing error",
            "Process the refund",
            "Confirm resolution",
        ],
        "expected_tools": ["billing_system", "payment_processor", "notification_service"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 10,
            "required_actions": ["verify", "refund", "confirm"]
        }
    }
    
    CUSTOMER_SERVICE_COMPLEX = {
        "id": "cs-complex-001",
        "domain": "customer_service",
        "complexity": "complex",
        "task": "Handle a multi-issue customer escalation involving technical support and billing while maintaining compliance.",
        "expected_steps": [
            "Understand multiple customer issues",
            "Prioritize issues by severity",
            "Consult technical knowledge base",
            "Coordinate with billing department",
            "Apply compliance rules",
            "Develop comprehensive solution",
            "Implement solution",
            "Verify resolution",
            "Document case",
        ],
        "expected_tools": ["knowledge_base", "billing_system", "compliance_checker", "ticket_system"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 15,
            "required_domains": ["technical", "billing", "compliance"]
        }
    }
    
    # Software Development domain scenarios
    SOFTWARE_SIMPLE = {
        "id": "swe-simple-001",
        "domain": "software_development",
        "complexity": "simple",
        "task": "Write a function that calculates the sum of two numbers.",
        "expected_steps": [
            "Understand requirements",
            "Write function",
            "Test with examples",
        ],
        "expected_tools": ["code_editor", "test_runner"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 5,
            "required_output": "working_code"
        }
    }
    
    SOFTWARE_MODERATE = {
        "id": "swe-moderate-001",
        "domain": "software_development",
        "complexity": "moderate",
        "task": "Implement a REST API endpoint that handles user authentication with proper error handling.",
        "expected_steps": [
            "Design API specification",
            "Implement endpoint",
            "Add authentication logic",
            "Implement error handling",
            "Write tests",
            "Document API",
        ],
        "expected_tools": ["code_editor", "test_runner", "api_designer", "documentation_tool"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 10,
            "required_features": ["auth", "error_handling"]
        }
    }
    
    SOFTWARE_COMPLEX = {
        "id": "swe-complex-001",
        "domain": "software_development",
        "complexity": "complex",
        "task": "Design and implement a distributed caching system with consistency guarantees and failover support.",
        "expected_steps": [
            "Design architecture",
            "Define consistency model",
            "Implement core cache",
            "Add replication",
            "Implement failover",
            "Optimize performance",
            "Write comprehensive tests",
            "Document design",
            "Create deployment guide",
        ],
        "expected_tools": ["architecture_tool", "code_editor", "test_framework", "monitoring_tool"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 15,
            "required_properties": ["consistent", "resilient", "performant"]
        }
    }
    
    # Healthcare domain scenarios
    HEALTHCARE_SIMPLE = {
        "id": "health-simple-001",
        "domain": "healthcare",
        "complexity": "simple",
        "task": "Retrieve a patient's basic medical history.",
        "expected_steps": [
            "Identify patient",
            "Access medical records",
            "Compile history",
        ],
        "expected_tools": ["patient_database", "records_system"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 5,
            "required_info": ["medical_history"]
        }
    }
    
    HEALTHCARE_MODERATE = {
        "id": "health-moderate-001",
        "domain": "healthcare",
        "complexity": "moderate",
        "task": "Analyze patient symptoms and suggest appropriate diagnostic tests while checking for drug interactions.",
        "expected_steps": [
            "Record patient symptoms",
            "Review medical history",
            "Check current medications",
            "Identify drug interactions",
            "Recommend diagnostic tests",
            "Document recommendations",
        ],
        "expected_tools": ["symptom_analyzer", "interaction_checker", "diagnostic_guide"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 10,
            "required_checks": ["drug_interaction", "diagnostic"]
        }
    }
    
    HEALTHCARE_COMPLEX = {
        "id": "health-complex-001",
        "domain": "healthcare",
        "complexity": "complex",
        "task": "Develop a treatment plan for a complex multi-morbidity patient with regulatory and ethical considerations.",
        "expected_steps": [
            "Comprehensive assessment",
            "Review all conditions",
            "Check current medications",
            "Assess contraindications",
            "Review guidelines",
            "Evaluate comorbidities",
            "Develop prioritized plan",
            "Document rationale",
            "Plan follow-up",
        ],
        "expected_tools": ["clinical_guidelines", "interaction_checker", "medical_ai", "documentation_system"],
        "success_criteria": {
            "must_use_tool": True,
            "max_steps": 15,
            "required_considerations": ["comorbidity", "contraindication", "guideline_compliance"]
        }
    }


class ScenarioLoader:
    """Load and customize test scenarios based on domain and complexity."""
    
    # Map domains to their scenario templates
    DOMAIN_SCENARIOS = {
        "customer_service": {
            "simple": ScenarioTemplate.CUSTOMER_SERVICE_SIMPLE,
            "moderate": ScenarioTemplate.CUSTOMER_SERVICE_MODERATE,
            "complex": ScenarioTemplate.CUSTOMER_SERVICE_COMPLEX,
        },
        "software_development": {
            "simple": ScenarioTemplate.SOFTWARE_SIMPLE,
            "moderate": ScenarioTemplate.SOFTWARE_MODERATE,
            "complex": ScenarioTemplate.SOFTWARE_COMPLEX,
        },
        "healthcare": {
            "simple": ScenarioTemplate.HEALTHCARE_SIMPLE,
            "moderate": ScenarioTemplate.HEALTHCARE_MODERATE,
            "complex": ScenarioTemplate.HEALTHCARE_COMPLEX,
        },
    }
    
    # Fallback generic scenarios
    GENERIC_SCENARIOS = {
        "simple": {
            "id": "generic-simple",
            "domain": "general",
            "complexity": "simple",
            "task": "Complete a simple task.",
            "expected_steps": ["Understand task", "Execute", "Verify"],
            "expected_tools": ["executor"],
            "success_criteria": {"must_use_tool": True}
        },
        "moderate": {
            "id": "generic-moderate",
            "domain": "general",
            "complexity": "moderate",
            "task": "Complete a moderate complexity task with multiple steps.",
            "expected_steps": ["Plan", "Execute step 1", "Execute step 2", "Verify", "Document"],
            "expected_tools": ["executor", "verifier"],
            "success_criteria": {"must_use_tool": True}
        },
        "complex": {
            "id": "generic-complex",
            "domain": "general",
            "complexity": "complex",
            "task": "Complete a complex task requiring multiple tools and coordination.",
            "expected_steps": ["Plan", "Execute phase 1", "Execute phase 2", "Integrate", "Test", "Verify", "Document"],
            "expected_tools": ["executor", "integrator", "verifier"],
            "success_criteria": {"must_use_tool": True}
        },
    }
    
    @staticmethod
    def get_scenario(
        domain: Optional[str] = None,
        complexity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a test scenario for the given domain and complexity.
        
        Args:
            domain: Agent domain (customer_service, software_development, healthcare, etc.)
            complexity: Task complexity (simple, moderate, complex, expert)
            
        Returns:
            Dictionary with scenario details
        """
        # Default complexity if not specified
        if complexity is None:
            complexity = "moderate"
        
        # Normalize complexity string
        complexity = complexity.lower().strip()
        
        # Try to get domain-specific scenario
        if domain:
            domain = domain.lower().strip()
            if domain in ScenarioLoader.DOMAIN_SCENARIOS:
                domain_scenarios = ScenarioLoader.DOMAIN_SCENARIOS[domain]
                if complexity in domain_scenarios:
                    scenario = domain_scenarios[complexity].copy()
                    return scenario
        
        # Fall back to generic scenario
        if complexity in ScenarioLoader.GENERIC_SCENARIOS:
            return ScenarioLoader.GENERIC_SCENARIOS[complexity].copy()
        
        # Ultimate fallback to moderate generic
        return ScenarioLoader.GENERIC_SCENARIOS["moderate"].copy()
    
    @staticmethod
    def get_all_domains() -> List[str]:
        """Get list of all supported domains."""
        return list(ScenarioLoader.DOMAIN_SCENARIOS.keys())
    
    @staticmethod
    def get_complexities_for_domain(domain: str) -> List[str]:
        """Get available complexity levels for a domain."""
        domain = domain.lower().strip()
        if domain in ScenarioLoader.DOMAIN_SCENARIOS:
            return list(ScenarioLoader.DOMAIN_SCENARIOS[domain].keys())
        return ["simple", "moderate", "complex"]
