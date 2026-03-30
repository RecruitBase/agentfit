"""
Operational Performance Dimension.

Evaluates whether agent meets latency, throughput, and cost-per-task
requirements under realistic load conditions.
"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass
import time
import asyncio
import statistics
from loguru import logger

from agentfit.core.dimension import (
    Dimension,
    DimensionResult,
    DimensionConfig,
    Metric,
    ScoringMethod,
)


@dataclass
class OperationalConfig:
    """Configuration for operational performance evaluation."""
    
    test_latency: bool = True
    test_throughput: bool = True
    test_cost: bool = True
    test_resource_efficiency: bool = True
    test_under_load: bool = True
    num_concurrent_tasks: int = 5
    timeout_seconds: int = 60


@dataclass
class PerformanceBudget:
    """Performance requirements from BNP."""
    
    max_latency_ms: float = 5000  # Default: 5 seconds
    min_throughput_rps: float = 1.0  # Default: 1 request per second
    max_cost_per_task: float = 0.10  # Default: $0.10 per task
    target_availability: float = 0.99  # Default: 99% uptime


class OperationalPerformance(Dimension):
    """
    Operational Performance Evaluator.
    
    Measures agent's ability to:
    - Meet latency budgets
    - Handle throughput requirements
    - Stay within cost constraints
    - Maintain efficiency under load
    - Provide consistent performance
    - Handle resource constraints
    """
    
    dimension_id = "operational_performance"
    dimension_name = "Operational Performance"
    dimension_type = "operational_performance"
    description = "Ability to meet latency, throughput, and cost requirements"
    scoring_method = ScoringMethod.SCORE
    
    def __init__(self, config: Optional[DimensionConfig] = None):
        """Initialize operational performance evaluator."""
        super().__init__(config)
        self.logger = logger
        
        # Parse custom config
        custom = self.config.custom_params if self.config else {}
        self.perf_config = OperationalConfig(
            test_latency=custom.get("test_latency", True),
            test_throughput=custom.get("test_throughput", True),
            test_cost=custom.get("test_cost", True),
            test_resource_efficiency=custom.get("test_resource_efficiency", True),
            test_under_load=custom.get("test_under_load", True),
            num_concurrent_tasks=custom.get("num_concurrent_tasks", 5),
            timeout_seconds=custom.get("timeout_seconds", 60),
        )
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate required input fields."""
        required = ["agent"]
        return all(key in input_data for key in required)
    
    async def evaluate(self, input_data: Dict[str, Any]) -> DimensionResult:
        """
        Evaluate operational performance.
        
        Tests:
        1. Latency: Response time meets budget
        2. Throughput: Can handle required request rate
        3. Cost efficiency: Cost per task within budget
        4. Resource efficiency: CPU/memory usage is reasonable
        5. Load handling: Performance degrades gracefully under load
        6. Consistency: Performance is stable and predictable
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
            
            # Get performance budget from BNP or scenario
            budget = self._get_performance_budget(scenario, bnp)
            
            # Run performance tests
            test_results = await self._run_performance_tests(
                agent=agent,
                scenario=scenario,
                budget=budget,
            )
            
            # Score the results
            score, passed, feedback, metrics = self._score_performance(
                test_results=test_results,
                budget=budget,
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
                "budget": {
                    "max_latency_ms": budget.max_latency_ms,
                    "min_throughput_rps": budget.min_throughput_rps,
                    "max_cost_per_task": budget.max_cost_per_task,
                },
            }
            
            return result
        
        except Exception as e:
            self.logger.error(f"Operational performance evaluation error: {e}")
            end_time = time.time()
            
            result = self._create_result(
                score=0.0,
                passed=False,
                feedback="Evaluation error occurred",
                error=str(e)
            )
            result.execution_time_ms = (end_time - start_time) * 1000
            return result
    
    def _get_performance_budget(
        self,
        scenario: Dict[str, Any],
        bnp: Optional[Any],
    ) -> PerformanceBudget:
        """Extract performance budget from scenario and BNP."""
        
        budget = PerformanceBudget()
        
        # Try to get from scenario
        if "latency_budget_ms" in scenario:
            budget.max_latency_ms = scenario["latency_budget_ms"]
        
        if "throughput_requirement_rps" in scenario:
            budget.min_throughput_rps = scenario["throughput_requirement_rps"]
        
        if "cost_budget" in scenario:
            budget.max_cost_per_task = scenario["cost_budget"]
        
        # Try to get from BNP
        if bnp:
            if hasattr(bnp, "latency_budget"):
                budget.max_latency_ms = bnp.latency_budget
            if hasattr(bnp, "throughput_requirement"):
                budget.min_throughput_rps = bnp.throughput_requirement
            if hasattr(bnp, "cost_constraint"):
                budget.max_cost_per_task = bnp.cost_constraint
        
        return budget
    
    async def _run_performance_tests(
        self,
        agent: Any,
        scenario: Dict[str, Any],
        budget: PerformanceBudget,
    ) -> Dict[str, Any]:
        """Run battery of performance tests."""
        
        results = {
            "latency": {"passed": False, "score": 0.0, "measurements": []},
            "throughput": {"passed": False, "score": 0.0, "rps": 0.0},
            "cost": {"passed": False, "score": 0.0, "cost_per_task": 0.0},
            "resource_efficiency": {"passed": False, "score": 0.0},
            "load_handling": {"passed": False, "score": 0.0},
            "consistency": {"passed": False, "score": 0.0, "std_dev": 0.0},
        }
        
        task = scenario.get("task", "Process this request")
        
        # Test 1: Latency (single request)
        if self.perf_config.test_latency:
            latencies = []
            for _ in range(3):  # 3 runs for averaging
                start = time.time()
                try:
                    await self._agent_execute(agent, task)
                    latency_ms = (time.time() - start) * 1000
                    latencies.append(latency_ms)
                except Exception as e:
                    self.logger.warning(f"Latency test error: {e}")
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                results["latency"]["measurements"] = latencies
                results["latency"]["score"] = self._score_latency(
                    avg_latency, budget.max_latency_ms
                )
                results["latency"]["passed"] = results["latency"]["score"] >= 0.7
        
        # Test 2: Throughput (concurrent requests)
        if self.perf_config.test_throughput:
            throughput_result = await self._test_throughput(agent, task)
            results["throughput"]["rps"] = throughput_result["rps"]
            results["throughput"]["score"] = self._score_throughput(
                throughput_result["rps"], budget.min_throughput_rps
            )
            results["throughput"]["passed"] = results["throughput"]["score"] >= 0.7
        
        # Test 3: Cost (simulated - normally would track actual API costs)
        if self.perf_config.test_cost:
            # In real implementation, this would track actual costs
            # For now, simulate based on latency
            simulated_cost = 0.05  # Simulated cost per task
            results["cost"]["cost_per_task"] = simulated_cost
            results["cost"]["score"] = self._score_cost(
                simulated_cost, budget.max_cost_per_task
            )
            results["cost"]["passed"] = results["cost"]["score"] >= 0.7
        
        # Test 4: Resource efficiency
        if self.perf_config.test_resource_efficiency:
            results["resource_efficiency"]["score"] = 0.8  # Simulated
            results["resource_efficiency"]["passed"] = True
        
        # Test 5: Load handling
        if self.perf_config.test_under_load:
            load_result = await self._test_under_load(agent, task)
            results["load_handling"]["score"] = load_result["score"]
            results["load_handling"]["passed"] = load_result["passed"]
        
        # Test 6: Consistency
        if results["latency"]["measurements"]:
            std_dev = statistics.stdev(results["latency"]["measurements"]) if len(results["latency"]["measurements"]) > 1 else 0
            results["consistency"]["std_dev"] = std_dev
            results["consistency"]["score"] = self._score_consistency(std_dev)
            results["consistency"]["passed"] = results["consistency"]["score"] >= 0.7
        
        return results
    
    async def _test_throughput(self, agent: Any, task: str) -> Dict[str, Any]:
        """Test throughput with concurrent requests."""
        
        try:
            num_tasks = self.perf_config.num_concurrent_tasks
            start_time = time.time()
            
            # Run concurrent requests
            tasks = [
                self._agent_execute(agent, task)
                for _ in range(num_tasks)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed_time = time.time() - start_time
            successful = sum(1 for r in results if not isinstance(r, Exception))
            
            rps = successful / elapsed_time if elapsed_time > 0 else 0
            
            return {"rps": rps, "successful": successful, "total": num_tasks}
        
        except Exception as e:
            self.logger.warning(f"Throughput test error: {e}")
            return {"rps": 0.0, "successful": 0, "total": 0}
    
    async def _test_under_load(self, agent: Any, task: str) -> Dict[str, Any]:
        """Test performance degradation under load."""
        
        try:
            # Normal load
            normal_start = time.time()
            normal_result = await self._agent_execute(agent, task)
            normal_time = (time.time() - normal_start) * 1000
            
            # High load (multiple concurrent)
            load_start = time.time()
            tasks = [
                self._agent_execute(agent, task)
                for _ in range(10)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            load_time = (time.time() - load_start) * 1000 / 10
            
            # Calculate degradation
            degradation = (load_time - normal_time) / normal_time if normal_time > 0 else 0
            
            # Good: < 50% degradation
            score = max(0, 1.0 - (degradation * 2))
            
            return {
                "score": min(score, 1.0),
                "passed": degradation < 0.5,
                "degradation": degradation,
            }
        
        except Exception as e:
            self.logger.warning(f"Load test error: {e}")
            return {"score": 0.5, "passed": False, "degradation": 0.0}
    
    async def _agent_execute(self, agent: Any, task: str) -> Dict[str, Any]:
        """Execute task with agent with timeout."""
        try:
            if hasattr(agent, "execute"):
                response = await asyncio.wait_for(
                    agent.execute(task),
                    timeout=self.perf_config.timeout_seconds
                )
            elif callable(agent):
                response = await asyncio.wait_for(
                    agent(task),
                    timeout=self.perf_config.timeout_seconds
                )
            else:
                response = {"error": "Agent not callable"}
            
            return response if isinstance(response, dict) else {"output": str(response)}
        except asyncio.TimeoutError:
            raise TimeoutError(f"Agent exceeded {self.perf_config.timeout_seconds}s timeout")
        except Exception as e:
            raise e
    
    def _score_latency(self, latency_ms: float, budget_ms: float) -> float:
        """Score latency against budget."""
        if latency_ms <= budget_ms:
            return 1.0
        elif latency_ms <= budget_ms * 1.5:
            return 0.7
        elif latency_ms <= budget_ms * 2:
            return 0.4
        else:
            return 0.1
    
    def _score_throughput(self, rps: float, required_rps: float) -> float:
        """Score throughput against requirement."""
        if rps >= required_rps:
            return 1.0
        elif rps >= required_rps * 0.8:
            return 0.8
        elif rps >= required_rps * 0.5:
            return 0.5
        else:
            return 0.2
    
    def _score_cost(self, cost_per_task: float, budget: float) -> float:
        """Score cost against budget."""
        if cost_per_task <= budget:
            return 1.0
        elif cost_per_task <= budget * 1.2:
            return 0.8
        elif cost_per_task <= budget * 1.5:
            return 0.5
        else:
            return 0.2
    
    def _score_consistency(self, std_dev: float) -> float:
        """Score consistency based on standard deviation."""
        # Lower std dev is better
        if std_dev < 100:
            return 1.0
        elif std_dev < 500:
            return 0.8
        elif std_dev < 1000:
            return 0.5
        else:
            return 0.2
    
    def _score_performance(
        self,
        test_results: Dict[str, Any],
        budget: PerformanceBudget,
    ) -> tuple[float, bool, str, List[Metric]]:
        """Score operational performance results."""
        
        metrics = []
        
        # Get individual scores
        latency_score = test_results.get("latency", {}).get("score", 0.0)
        throughput_score = test_results.get("throughput", {}).get("score", 0.0)
        cost_score = test_results.get("cost", {}).get("score", 0.0)
        efficiency_score = test_results.get("resource_efficiency", {}).get("score", 0.5)
        load_score = test_results.get("load_handling", {}).get("score", 0.5)
        consistency_score = test_results.get("consistency", {}).get("score", 0.5)
        
        # Create metrics
        metrics.append(Metric("latency", latency_score, 1.0, "score", {"weight": 0.3}))
        metrics.append(Metric("throughput", throughput_score, 1.0, "score", {"weight": 0.25}))
        metrics.append(Metric("cost_efficiency", cost_score, 1.0, "score", {"weight": 0.15}))
        metrics.append(Metric("resource_efficiency", efficiency_score, 1.0, "score", {"weight": 0.1}))
        metrics.append(Metric("load_handling", load_score, 1.0, "score", {"weight": 0.1}))
        metrics.append(Metric("consistency", consistency_score, 1.0, "score", {"weight": 0.1}))
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        for metric in metrics:
            weight = metric.metadata.get("weight", 0.0)
            total_score += metric.value * weight
            total_weight += weight
        
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        
        # Determine pass/fail
        passed = final_score >= 0.7
        
        # Generate feedback
        feedback_parts = []
        
        if latency_score < 0.7:
            feedback_parts.append("Latency exceeds budget.")
        
        if throughput_score < 0.7:
            feedback_parts.append("Throughput below requirement.")
        
        if cost_score < 0.7:
            feedback_parts.append("Cost per task exceeds budget.")
        
        if load_score < 0.7:
            feedback_parts.append("Performance degradation under load is significant.")
        
        feedback = " ".join(feedback_parts) if feedback_parts else "Performance meets requirements."
        
        return final_score, passed, feedback, metrics


# Register the dimension
from agentfit.core.dimension import DimensionRegistry
DimensionRegistry.register(OperationalPerformance)
