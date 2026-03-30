"""
Deployment Compatibility Dimension.

Evaluates whether agent can be deployed, integrated, and maintained
within the org's infrastructure constraints.
"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import time
import asyncio
from loguru import logger

from agentfit.core.dimension import (
    Dimension,
    DimensionResult,
    DimensionConfig,
    Metric,
    ScoringMethod,
)


class DeploymentModel(str, Enum):
    """Deployment models."""
    CLOUD_ONLY = "cloud_only"
    ON_PREMISE = "on_premise"
    HYBRID = "hybrid"
    AIRGAPPED = "airgapped"


@dataclass
class DeploymentConfig:
    """Configuration for deployment compatibility evaluation."""
    
    test_containerization: bool = True
    test_api_surface: bool = True
    test_monitoring: bool = True
    test_scaling: bool = True
    test_update_mechanism: bool = True
    test_infrastructure_fit: bool = True
    timeout_seconds: int = 30


class DeploymentCompatibility(Dimension):
    """
    Deployment Compatibility Evaluator.
    
    Novel dimension testing:
    - Self-hosting capability
    - API surface adequacy
    - Containerization support
    - Environment isolation
    - Update/rollback procedures
    - Monitoring and observability
    - Scalability support
    """
    
    dimension_id = "deployment_compatibility"
    dimension_name = "Deployment Compatibility"
    dimension_type = "deployment_compatibility"
    description = "Ability to deploy and maintain within infrastructure constraints"
    scoring_method = ScoringMethod.SCORE
    
    def __init__(self, config: Optional[DimensionConfig] = None):
        """Initialize deployment compatibility evaluator."""
        super().__init__(config)
        self.logger = logger
        
        # Parse custom config
        custom = self.config.custom_params if self.config else {}
        self.deploy_config = DeploymentConfig(
            test_containerization=custom.get("test_containerization", True),
            test_api_surface=custom.get("test_api_surface", True),
            test_monitoring=custom.get("test_monitoring", True),
            test_scaling=custom.get("test_scaling", True),
            test_update_mechanism=custom.get("test_update_mechanism", True),
            test_infrastructure_fit=custom.get("test_infrastructure_fit", True),
            timeout_seconds=custom.get("timeout_seconds", 30),
        )
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate required input fields."""
        required = ["agent"]
        return all(key in input_data for key in required)
    
    async def evaluate(self, input_data: Dict[str, Any]) -> DimensionResult:
        """
        Evaluate deployment compatibility.
        
        Tests:
        1. Containerization: Can run in Docker/containers
        2. API surface: Clear, documented interface
        3. Monitoring: Provides observability hooks
        4. Scaling: Supports horizontal/vertical scaling
        5. Updates: Safe update/rollback procedures
        6. Infrastructure fit: Meets org's deployment model
        7. Dependency management: Clean dependency trees
        8. Resource isolation: Supports multi-tenancy
        """
        start_time = time.time()
        
        try:
            agent = input_data.get("agent")
            scenario = input_data.get("scenario", {})
            bnp = input_data.get("bnp")
            
            if not agent:
                return self._create_result(
                    score=0.0,
                    passed=False,
                    feedback="Missing required agent",
                    error="Invalid input data"
                )
            
            # Determine deployment requirements
            deployment_reqs = self._get_deployment_requirements(scenario, bnp)
            
            # Run deployment tests
            test_results = await self._run_deployment_tests(
                agent=agent,
                scenario=scenario,
                deployment_reqs=deployment_reqs,
            )
            
            # Score the results
            score, passed, feedback, metrics = self._score_deployment(
                test_results=test_results,
                deployment_reqs=deployment_reqs,
            )
            
            # Create result
            end_time = time.time()
            result = self._create_result(
                score=score,
                passed=passed,
                feedback=feedback,
                metrics=metrics,
            )
            result.execution_time_ms = (end_time - start_time) * 1000
            result.metadata = {
                "test_results": test_results,
                "deployment_model": deployment_reqs.get("model", "hybrid"),
            }
            
            return result
        
        except Exception as e:
            self.logger.error(f"Deployment compatibility evaluation error: {e}")
            end_time = time.time()
            
            result = self._create_result(
                score=0.0,
                passed=False,
                feedback="Evaluation error occurred",
                error=str(e)
            )
            result.execution_time_ms = (end_time - start_time) * 1000
            return result
    
    def _get_deployment_requirements(
        self,
        scenario: Dict[str, Any],
        bnp: Optional[Any],
    ) -> Dict[str, Any]:
        """Extract deployment requirements from scenario and BNP."""
        
        reqs = {
            "model": "hybrid",  # Default to hybrid
            "requires_on_premise": False,
            "requires_airgapped": False,
            "max_memory_gb": 8,
            "max_cpu_cores": 4,
        }
        
        # Try to get from scenario
        if "deployment_model" in scenario:
            reqs["model"] = scenario["deployment_model"]
        
        if "infrastructure_constraint" in scenario:
            constraint = scenario["infrastructure_constraint"]
            if "on-premise" in constraint.lower():
                reqs["requires_on_premise"] = True
            if "airgapped" in constraint.lower():
                reqs["requires_airgapped"] = True
        
        # Try to get from BNP
        if bnp:
            if hasattr(bnp, "infrastructure_constraint"):
                constraint = bnp.infrastructure_constraint
                if constraint == "on-premise":
                    reqs["requires_on_premise"] = True
                    reqs["model"] = "on_premise"
                elif constraint == "airgapped":
                    reqs["requires_airgapped"] = True
                    reqs["model"] = "airgapped"
        
        return reqs
    
    async def _run_deployment_tests(
        self,
        agent: Any,
        scenario: Dict[str, Any],
        deployment_reqs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run battery of deployment tests."""
        
        results = {
            "containerization": {"passed": False, "score": 0.0},
            "api_surface": {"passed": False, "score": 0.0},
            "monitoring": {"passed": False, "score": 0.0},
            "scaling": {"passed": False, "score": 0.0},
            "update_mechanism": {"passed": False, "score": 0.0},
            "infrastructure_fit": {"passed": False, "score": 0.0},
            "dependency_management": {"passed": False, "score": 0.0},
            "resource_isolation": {"passed": False, "score": 0.0},
        }
        
        # Test 1: Containerization
        if self.deploy_config.test_containerization:
            container_test = (
                "Describe how this agent can be containerized and deployed in Docker. "
                "What base image, dependencies, and entry points are needed?"
            )
            response = await self._agent_execute(agent, container_test)
            score = self._score_containerization(response)
            results["containerization"]["score"] = score
            results["containerization"]["passed"] = score >= 0.7
        
        # Test 2: API Surface
        if self.deploy_config.test_api_surface:
            api_test = (
                "What is your API surface? List endpoints, request/response formats, "
                "error codes, and authentication methods."
            )
            response = await self._agent_execute(agent, api_test)
            score = self._score_api_surface(response)
            results["api_surface"]["score"] = score
            results["api_surface"]["passed"] = score >= 0.7
        
        # Test 3: Monitoring
        if self.deploy_config.test_monitoring:
            monitoring_test = (
                "How does this agent support monitoring and observability? "
                "What metrics, logs, and traces does it provide?"
            )
            response = await self._agent_execute(agent, monitoring_test)
            score = self._score_monitoring(response)
            results["monitoring"]["score"] = score
            results["monitoring"]["passed"] = score >= 0.7
        
        # Test 4: Scaling
        if self.deploy_config.test_scaling:
            scaling_test = (
                "How does this agent support horizontal and vertical scaling? "
                "What are the scaling limitations and constraints?"
            )
            response = await self._agent_execute(agent, scaling_test)
            score = self._score_scaling(response)
            results["scaling"]["score"] = score
            results["scaling"]["passed"] = score >= 0.7
        
        # Test 5: Update Mechanism
        if self.deploy_config.test_update_mechanism:
            update_test = (
                "How are updates and rollbacks handled? "
                "What is the process for safe deployment and version management?"
            )
            response = await self._agent_execute(agent, update_test)
            score = self._score_update_mechanism(response)
            results["update_mechanism"]["score"] = score
            results["update_mechanism"]["passed"] = score >= 0.7
        
        # Test 6: Infrastructure Fit
        if self.deploy_config.test_infrastructure_fit:
            if deployment_reqs.get("requires_on_premise") or deployment_reqs.get("requires_airgapped"):
                fit_test = (
                    "Does this agent support on-premise or airgapped deployment? "
                    "What are the requirements and limitations?"
                )
            else:
                fit_test = (
                    "What cloud platforms does this agent support? "
                    "How is it deployed in each?"
                )
            response = await self._agent_execute(agent, fit_test)
            score = self._score_infrastructure_fit(response, deployment_reqs)
            results["infrastructure_fit"]["score"] = score
            results["infrastructure_fit"]["passed"] = score >= 0.7
        
        # Test 7: Dependency Management
        if self.deploy_config.test_infrastructure_fit:
            dependency_test = (
                "What are the external dependencies? "
                "What libraries, services, or APIs are required?"
            )
            response = await self._agent_execute(agent, dependency_test)
            score = self._score_dependency_management(response)
            results["dependency_management"]["score"] = score
            results["dependency_management"]["passed"] = score >= 0.6
        
        # Test 8: Resource Isolation
        if self.deploy_config.test_infrastructure_fit:
            isolation_test = (
                "How does this agent handle resource isolation and multi-tenancy? "
                "What happens when multiple instances run concurrently?"
            )
            response = await self._agent_execute(agent, isolation_test)
            score = self._score_resource_isolation(response)
            results["resource_isolation"]["score"] = score
            results["resource_isolation"]["passed"] = score >= 0.6
        
        return results
    
    async def _agent_execute(self, agent: Any, prompt: str) -> Dict[str, Any]:
        """Execute prompt with agent with timeout."""
        try:
            if hasattr(agent, "execute"):
                response = await asyncio.wait_for(
                    agent.execute(prompt),
                    timeout=self.deploy_config.timeout_seconds
                )
            elif callable(agent):
                response = await asyncio.wait_for(
                    agent(prompt),
                    timeout=self.deploy_config.timeout_seconds
                )
            else:
                response = {"error": "Agent not callable"}
            
            return response if isinstance(response, dict) else {"output": str(response)}
        except asyncio.TimeoutError:
            return {"error": "timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    def _score_containerization(self, response: Dict[str, Any]) -> float:
        """Score containerization support."""
        output = str(response.get("output", "")).lower()
        
        indicators = ["docker", "container", "dockerfile", "image", "registry", "compose"]
        matched = sum(1 for ind in indicators if ind in output)
        
        return min(matched / len(indicators), 1.0)
    
    def _score_api_surface(self, response: Dict[str, Any]) -> float:
        """Score API surface clarity."""
        output = str(response.get("output", "")).lower()
        
        indicators = [
            "endpoint", "request", "response", "format", "json", "error",
            "authentication", "api", "method", "status"
        ]
        matched = sum(1 for ind in indicators if ind in output)
        
        return min(matched / len(indicators), 1.0)
    
    def _score_monitoring(self, response: Dict[str, Any]) -> float:
        """Score monitoring and observability support."""
        output = str(response.get("output", "")).lower()
        
        indicators = [
            "metric", "log", "trace", "monitor", "observability", "dashboard",
            "alert", "health", "status", "prometheus"
        ]
        matched = sum(1 for ind in indicators if ind in output)
        
        return min(matched / len(indicators), 1.0)
    
    def _score_scaling(self, response: Dict[str, Any]) -> float:
        """Score scaling support."""
        output = str(response.get("output", "")).lower()
        
        indicators = [
            "horizontal", "vertical", "kubernetes", "replica", "load balance",
            "stateless", "sharding", "partition", "concurrent", "parallel"
        ]
        matched = sum(1 for ind in indicators if ind in output)
        
        return min(matched / len(indicators), 1.0)
    
    def _score_update_mechanism(self, response: Dict[str, Any]) -> float:
        """Score update and rollback mechanisms."""
        output = str(response.get("output", "")).lower()
        
        indicators = [
            "rollback", "version", "update", "deploy", "downtime", "zero-downtime",
            "canary", "gradual", "backup", "restore"
        ]
        matched = sum(1 for ind in indicators if ind in output)
        
        return min(matched / len(indicators), 1.0)
    
    def _score_infrastructure_fit(self, response: Dict[str, Any], reqs: Dict[str, Any]) -> float:
        """Score infrastructure fit."""
        output = str(response.get("output", "")).lower()
        
        if reqs.get("requires_on_premise"):
            indicators = ["on-premise", "on premise", "self-hosted", "local"]
        elif reqs.get("requires_airgapped"):
            indicators = ["airgapped", "air-gapped", "offline", "network isolation"]
        else:
            indicators = ["cloud", "aws", "azure", "gcp", "kubernetes"]
        
        matched = sum(1 for ind in indicators if ind in output)
        
        return min(matched / len(indicators), 1.0)
    
    def _score_dependency_management(self, response: Dict[str, Any]) -> float:
        """Score dependency management clarity."""
        output = str(response.get("output", "")).lower()
        
        # Good: Minimal, clear dependencies
        # Bad: Many undeclared or complex dependencies
        
        has_clear_deps = any(phrase in output for phrase in [
            "requirement", "dependency", "library", "package", "module", "version"
        ])
        
        has_minimal_deps = any(phrase in output for phrase in [
            "minimal", "few", "lightweight", "zero", "none required"
        ])
        
        score = 0.7 if has_clear_deps else 0.3
        if has_minimal_deps:
            score = min(score + 0.2, 1.0)
        
        return score
    
    def _score_resource_isolation(self, response: Dict[str, Any]) -> float:
        """Score resource isolation support."""
        output = str(response.get("output", "")).lower()
        
        indicators = [
            "isolation", "multi-tenant", "namespace", "resource quota", "container",
            "memory", "cpu", "network", "concurrent"
        ]
        matched = sum(1 for ind in indicators if ind in output)
        
        return min(matched / len(indicators), 1.0)
    
    def _score_deployment(
        self,
        test_results: Dict[str, Any],
        deployment_reqs: Dict[str, Any],
    ) -> tuple[float, bool, str, List[Metric]]:
        """Score deployment compatibility results."""
        
        metrics = []
        
        # Get individual scores
        container_score = test_results.get("containerization", {}).get("score", 0.0)
        api_score = test_results.get("api_surface", {}).get("score", 0.0)
        monitoring_score = test_results.get("monitoring", {}).get("score", 0.0)
        scaling_score = test_results.get("scaling", {}).get("score", 0.0)
        update_score = test_results.get("update_mechanism", {}).get("score", 0.0)
        infra_score = test_results.get("infrastructure_fit", {}).get("score", 0.0)
        dep_score = test_results.get("dependency_management", {}).get("score", 0.0)
        isolation_score = test_results.get("resource_isolation", {}).get("score", 0.0)
        
        # Create metrics
        metrics.append(Metric("containerization", container_score, 1.0, "score", {"weight": 0.15}))
        metrics.append(Metric("api_surface", api_score, 1.0, "score", {"weight": 0.15}))
        metrics.append(Metric("monitoring", monitoring_score, 1.0, "score", {"weight": 0.15}))
        metrics.append(Metric("scaling", scaling_score, 1.0, "score", {"weight": 0.15}))
        metrics.append(Metric("updates", update_score, 1.0, "score", {"weight": 0.15}))
        metrics.append(Metric("infrastructure_fit", infra_score, 1.0, "score", {"weight": 0.15}))
        metrics.append(Metric("dependencies", dep_score, 1.0, "score", {"weight": 0.05}))
        metrics.append(Metric("isolation", isolation_score, 1.0, "score", {"weight": 0.05}))
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        for metric in metrics:
            weight = metric.metadata.get("weight", 0.0)
            total_score += metric.value * weight
            total_weight += weight
        
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        
        # Determine pass/fail - infrastructure fit is critical
        passed = final_score >= 0.7 and infra_score >= 0.6
        
        # Generate feedback
        feedback_parts = []
        
        if container_score < 0.6:
            feedback_parts.append("Containerization support is limited.")
        
        if api_score < 0.6:
            feedback_parts.append("API surface is unclear or undocumented.")
        
        if monitoring_score < 0.6:
            feedback_parts.append("Monitoring and observability are insufficient.")
        
        if scaling_score < 0.6:
            feedback_parts.append("Scaling support is limited.")
        
        if update_score < 0.6:
            feedback_parts.append("Update and rollback procedures are unclear.")
        
        if infra_score < 0.6:
            feedback_parts.append("Does not fit infrastructure requirements.")
        
        feedback = " ".join(feedback_parts) if feedback_parts else "Deployment compatibility is good."
        
        return final_score, passed, feedback, metrics


# Register the dimension
from agentfit.core.dimension import DimensionRegistry
DimensionRegistry.register(DeploymentCompatibility)
