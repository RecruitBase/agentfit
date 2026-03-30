"""
Task Competence Dimension.

Evaluates an agent's ability to understand, plan, and execute complex tasks
with appropriate tool usage and error recovery.
"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass
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


@dataclass
class TaskCompetenceConfig:
    """Configuration for task competence evaluation."""
    max_attempts: int = 3
    timeout_seconds: int = 30
    penalize_failed_attempts: bool = True
    require_step_explanation: bool = True
    check_tool_appropriateness: bool = True


class TaskCompetence(Dimension):
    """
    Task Competence Evaluator.
    
    Measures agent's ability to:
    - Understand task requirements
    - Plan appropriate steps
    - Execute steps correctly
    - Recover from errors
    - Complete tasks within constraints
    """
    
    dimension_id = "task_competence"
    dimension_name = "Task Competence"
    dimension_type = "task_competence"
    description = "Ability to understand, plan, and execute complex tasks"
    scoring_method = ScoringMethod.SCORE
    
    def __init__(self, config: Optional[DimensionConfig] = None):
        """Initialize task competence evaluator."""
        super().__init__(config)
        self.logger = logger
        
        # Parse custom task competence config
        custom = self.config.custom_params if self.config else {}
        self.tc_config = TaskCompetenceConfig(
            max_attempts=custom.get("max_attempts", 3),
            timeout_seconds=custom.get("timeout_seconds", 30),
            penalize_failed_attempts=custom.get("penalize_failed_attempts", True),
            require_step_explanation=custom.get("require_step_explanation", True),
            check_tool_appropriateness=custom.get("check_tool_appropriateness", True),
        )
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate required input fields."""
        required = ["agent", "scenario"]
        return all(key in input_data for key in required)
    
    async def evaluate(self, input_data: Dict[str, Any]) -> DimensionResult:
        """
        Evaluate task competence.
        
        Scenario should contain:
        - task: Task description
        - expected_steps: List of expected subtasks
        - expected_tools: Tools that should be used
        - success_criteria: How to measure success
        """
        start_time = time.time()
        
        try:
            agent = input_data.get("agent")
            scenario = input_data.get("scenario", {})
            
            if not agent or not scenario:
                return self._create_result(
                    score=0.0,
                    passed=False,
                    feedback="Missing required agent or scenario",
                    error="Invalid input data"
                )
            
            # Extract task information
            task = scenario.get("task", "")
            expected_steps = scenario.get("expected_steps", [])
            expected_tools = scenario.get("expected_tools", [])
            success_criteria = scenario.get("success_criteria", {})
            
            if not task:
                return self._create_result(
                    score=0.0,
                    passed=False,
                    feedback="Task not specified in scenario",
                    error="Missing task"
                )
            
            # Run task execution with tracking
            execution_result = await self._execute_task(
                agent=agent,
                task=task,
                expected_steps=expected_steps,
                expected_tools=expected_tools,
                scenario=scenario,
            )
            
            # Score the execution
            score, passed, feedback, metrics = self._score_execution(
                execution_result=execution_result,
                expected_steps=expected_steps,
                expected_tools=expected_tools,
                success_criteria=success_criteria,
                scenario=scenario,
            )
            
            # Finalize result
            end_time = time.time()
            result = self._create_result(
                score=score,
                passed=passed,
                feedback=feedback,
                metrics=metrics,
            )
            result.execution_time_ms = (end_time - start_time) * 1000
            result.metadata = {
                "execution_result": execution_result,
                "config": {
                    "max_attempts": self.tc_config.max_attempts,
                    "timeout_seconds": self.tc_config.timeout_seconds,
                }
            }
            
            return result
        
        except Exception as e:
            self.logger.error(f"Task competence evaluation error: {e}")
            end_time = time.time()
            
            result = self._create_result(
                score=0.0,
                passed=False,
                feedback="Evaluation error occurred",
                error=str(e)
            )
            result.execution_time_ms = (end_time - start_time) * 1000
            return result
    
    async def _execute_task(
        self,
        agent: Any,
        task: str,
        expected_steps: List[str],
        expected_tools: List[str],
        scenario: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the task with the agent.
        
        Returns execution tracking data.
        """
        execution_log = {
            "task": task,
            "steps_executed": [],
            "tools_used": [],
            "errors": [],
            "success": False,
            "completion_time_ms": 0,
            "attempts": 0,
        }
        
        start_time = time.time()
        
        for attempt in range(self.tc_config.max_attempts):
            execution_log["attempts"] = attempt + 1
            
            try:
                # Call agent (simplified - real implementation would be more sophisticated)
                # This assumes agent is async callable or has async execute method
                if hasattr(agent, "execute"):
                    response = await asyncio.wait_for(
                        agent.execute(task, expected_tools=expected_tools),
                        timeout=self.tc_config.timeout_seconds
                    )
                elif callable(agent):
                    response = await asyncio.wait_for(
                        agent(task),
                        timeout=self.tc_config.timeout_seconds
                    )
                else:
                    execution_log["errors"].append("Agent is not callable")
                    continue
                
                # Parse response
                if isinstance(response, dict):
                    execution_log["success"] = response.get("success", False)
                    execution_log["steps_executed"] = response.get("steps", [])
                    execution_log["tools_used"] = response.get("tools_used", [])
                    execution_log["final_output"] = response.get("output", "")
                else:
                    execution_log["final_output"] = str(response)
                    execution_log["success"] = True
                
                if execution_log["success"]:
                    break
            
            except asyncio.TimeoutError:
                execution_log["errors"].append(f"Timeout on attempt {attempt + 1}")
            except Exception as e:
                execution_log["errors"].append(f"Error on attempt {attempt + 1}: {str(e)}")
        
        end_time = time.time()
        execution_log["completion_time_ms"] = (end_time - start_time) * 1000
        
        return execution_log
    
    def _score_execution(
        self,
        execution_result: Dict[str, Any],
        expected_steps: List[str],
        expected_tools: List[str],
        success_criteria: Dict[str, Any],
        scenario: Dict[str, Any],
    ) -> tuple[float, bool, str, List[Metric]]:
        """
        Score the execution based on multiple factors.
        
        Returns: (score, passed, feedback, metrics)
        """
        metrics = []
        
        # 1. Task success (40% weight)
        task_success = 1.0 if execution_result.get("success") else 0.0
        metrics.append(
            Metric(
                name="task_success",
                value=task_success,
                max_value=1.0,
                unit="binary",
                metadata={"weight": 0.4}
            )
        )
        
        # 2. Step completion (30% weight)
        executed_steps = execution_result.get("steps_executed", [])
        step_coverage = len(executed_steps) / max(len(expected_steps), 1) if expected_steps else 1.0
        step_coverage = min(step_coverage, 1.0)
        metrics.append(
            Metric(
                name="step_coverage",
                value=step_coverage,
                max_value=1.0,
                unit="ratio",
                metadata={"weight": 0.3}
            )
        )
        
        # 3. Tool appropriateness (20% weight)
        tools_used = execution_result.get("tools_used", [])
        tool_score = 1.0
        if self.tc_config.check_tool_appropriateness and expected_tools:
            correct_tools = sum(1 for t in tools_used if t in expected_tools)
            tool_score = correct_tools / len(expected_tools)
        metrics.append(
            Metric(
                name="tool_appropriateness",
                value=tool_score,
                max_value=1.0,
                unit="ratio",
                metadata={"weight": 0.2}
            )
        )
        
        # 4. Error recovery (10% weight)
        attempts = execution_result.get("attempts", 1)
        errors = execution_result.get("errors", [])
        
        # Penalize multiple attempts if configured
        recovery_penalty = 1.0
        if self.tc_config.penalize_failed_attempts and attempts > 1:
            recovery_penalty = 1.0 / (1.0 + (attempts - 1) * 0.2)
        
        metrics.append(
            Metric(
                name="error_recovery",
                value=recovery_penalty,
                max_value=1.0,
                unit="penalty",
                metadata={"weight": 0.1, "attempts": attempts}
            )
        )
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        for metric in metrics:
            weight = metric.metadata.get("weight", 0.0)
            total_score += metric.value * weight
            total_weight += weight
        
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        
        # Determine pass/fail
        passed = (
            execution_result.get("success", False) and
            step_coverage >= 0.8 and
            final_score >= 0.7
        )
        
        # Generate feedback
        feedback_parts = []
        if execution_result.get("success"):
            feedback_parts.append("Task completed successfully.")
        else:
            feedback_parts.append("Task was not completed successfully.")
        
        if errors:
            feedback_parts.append(f"Encountered {len(errors)} error(s).")
        
        feedback_parts.append(
            f"Step coverage: {step_coverage*100:.1f}%. "
            f"Tool appropriateness: {tool_score*100:.1f}%. "
            f"Attempts needed: {attempts}."
        )
        
        feedback = " ".join(feedback_parts)
        
        return final_score, passed, feedback, metrics


# Register the dimension
from agentfit.core.dimension import DimensionRegistry
DimensionRegistry.register(TaskCompetence)
