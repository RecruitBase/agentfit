"""
Tool Use Dimension.

Evaluates agent's ability to correctly identify, select, and invoke tools
with appropriate parameters and error handling.
"""

from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass
import time
import asyncio
import json
from loguru import logger

from agentfit.core.dimension import (
    Dimension,
    DimensionResult,
    DimensionConfig,
    Metric,
    ScoringMethod,
)


@dataclass
class ToolUseConfig:
    """Configuration for tool use evaluation."""
    require_correct_params: bool = True
    penalize_incorrect_params: bool = True
    penalize_unused_tools: bool = False
    penalize_extra_tools: bool = True
    timeout_per_call_seconds: int = 10
    max_tool_calls: int = 20


class MockToolEnvironment:
    """Mock tool execution environment for testing."""
    
    def __init__(self, tools: Dict[str, Callable]):
        """
        Initialize with tool definitions.
        
        Args:
            tools: Dict mapping tool names to callables
        """
        self.tools = tools
        self.call_log: List[Dict[str, Any]] = []
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and log the call.
        
        Returns execution result.
        """
        result = {
            "tool": tool_name,
            "params": params,
            "success": False,
            "output": None,
            "error": None,
        }
        
        if tool_name not in self.tools:
            result["error"] = f"Tool '{tool_name}' not found"
            self.call_log.append(result)
            return result
        
        try:
            tool_func = self.tools[tool_name]
            output = await tool_func(**params) if asyncio.iscoroutinefunction(tool_func) else tool_func(**params)
            result["success"] = True
            result["output"] = output
        except TypeError as e:
            result["error"] = f"Invalid parameters: {str(e)}"
        except Exception as e:
            result["error"] = f"Execution error: {str(e)}"
        
        self.call_log.append(result)
        return result


class ToolUse(Dimension):
    """
    Tool Use Evaluator.
    
    Measures agent's ability to:
    - Identify when tools are needed
    - Select appropriate tools
    - Call tools with correct parameters
    - Handle tool errors gracefully
    - Use tool outputs effectively
    """
    
    dimension_id = "tool_use"
    dimension_name = "Tool Use"
    dimension_type = "tool_use"
    description = "Ability to correctly identify, select, and invoke tools"
    scoring_method = ScoringMethod.SCORE
    
    def __init__(self, config: Optional[DimensionConfig] = None):
        """Initialize tool use evaluator."""
        super().__init__(config)
        self.logger = logger
        
        # Parse custom tool use config
        custom = self.config.custom_params if self.config else {}
        self.tu_config = ToolUseConfig(
            require_correct_params=custom.get("require_correct_params", True),
            penalize_incorrect_params=custom.get("penalize_incorrect_params", True),
            penalize_unused_tools=custom.get("penalize_unused_tools", False),
            penalize_extra_tools=custom.get("penalize_extra_tools", True),
            timeout_per_call_seconds=custom.get("timeout_per_call_seconds", 10),
            max_tool_calls=custom.get("max_tool_calls", 20),
        )
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate required input fields."""
        required = ["agent", "scenario"]
        return all(key in input_data for key in required)
    
    async def evaluate(self, input_data: Dict[str, Any]) -> DimensionResult:
        """
        Evaluate tool use capabilities.
        
        Scenario should contain:
        - tools: Dict of tool definitions
        - task: Task that requires tool use
        - required_tools: List of tools that must be used
        - expected_tool_calls: List of expected tool invocations
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
            
            # Extract tool and task information
            tools_def = scenario.get("tools", {})
            task = scenario.get("task", "")
            required_tools = scenario.get("required_tools", [])
            expected_calls = scenario.get("expected_tool_calls", [])
            
            if not tools_def or not task:
                return self._create_result(
                    score=0.0,
                    passed=False,
                    feedback="Tools or task not specified",
                    error="Missing scenario data"
                )
            
            # Create tool environment
            tool_env = await self._setup_tool_environment(tools_def)
            
            # Execute agent with tool access
            execution_result = await self._execute_with_tools(
                agent=agent,
                task=task,
                tool_environment=tool_env,
            )
            
            # Score the tool usage
            score, passed, feedback, metrics = self._score_tool_usage(
                execution_result=execution_result,
                required_tools=required_tools,
                expected_calls=expected_calls,
                tool_env=tool_env,
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
                "tool_calls": tool_env.call_log,
                "execution_result": execution_result,
            }
            
            return result
        
        except Exception as e:
            self.logger.error(f"Tool use evaluation error: {e}")
            end_time = time.time()
            
            result = self._create_result(
                score=0.0,
                passed=False,
                feedback="Evaluation error occurred",
                error=str(e)
            )
            result.execution_time_ms = (end_time - start_time) * 1000
            return result
    
    async def _setup_tool_environment(
        self,
        tools_def: Dict[str, Any]
    ) -> MockToolEnvironment:
        """
        Setup mock tool environment.
        
        Converts tool definitions to callables.
        """
        async def mock_tool(**kwargs) -> Dict[str, Any]:
            """Mock tool that always succeeds."""
            return {
                "status": "success",
                "result": f"Executed with params: {kwargs}",
                "data": kwargs,
            }
        
        # Convert tool definitions to callables
        tools = {}
        for tool_name, tool_spec in tools_def.items():
            tools[tool_name] = mock_tool
        
        return MockToolEnvironment(tools)
    
    async def _execute_with_tools(
        self,
        agent: Any,
        task: str,
        tool_environment: MockToolEnvironment,
    ) -> Dict[str, Any]:
        """
        Execute agent with tool access.
        
        Returns execution tracking data.
        """
        execution_log = {
            "task": task,
            "success": False,
            "tool_calls": [],
            "errors": [],
            "final_output": None,
        }
        
        try:
            # Pass tool environment to agent (simplified)
            if hasattr(agent, "execute_with_tools"):
                response = await asyncio.wait_for(
                    agent.execute_with_tools(task, tools=tool_environment),
                    timeout=self.tu_config.timeout_per_call_seconds * self.tu_config.max_tool_calls
                )
            elif hasattr(agent, "execute"):
                response = await asyncio.wait_for(
                    agent.execute(task, tools=tool_environment.tools),
                    timeout=self.tu_config.timeout_per_call_seconds * self.tu_config.max_tool_calls
                )
            elif callable(agent):
                response = await asyncio.wait_for(
                    agent(task),
                    timeout=self.tu_config.timeout_per_call_seconds * self.tu_config.max_tool_calls
                )
            else:
                execution_log["errors"].append("Agent is not callable")
                return execution_log
            
            # Parse response
            if isinstance(response, dict):
                execution_log["success"] = response.get("success", False)
                execution_log["final_output"] = response.get("output", "")
            else:
                execution_log["final_output"] = str(response)
                execution_log["success"] = True
        
        except asyncio.TimeoutError:
            execution_log["errors"].append("Tool execution timeout")
        except Exception as e:
            execution_log["errors"].append(f"Execution error: {str(e)}")
        
        # Collect tool calls from environment
        execution_log["tool_calls"] = tool_environment.call_log
        
        return execution_log
    
    def _score_tool_usage(
        self,
        execution_result: Dict[str, Any],
        required_tools: List[str],
        expected_calls: List[Dict[str, Any]],
        tool_env: MockToolEnvironment,
        scenario: Dict[str, Any],
    ) -> tuple[float, bool, str, List[Metric]]:
        """
        Score tool usage based on multiple factors.
        
        Returns: (score, passed, feedback, metrics)
        """
        metrics = []
        tool_calls = tool_env.call_log
        
        # 1. Tool selection (40% weight)
        tools_used = [call["tool"] for call in tool_calls if call["success"]]
        required_used = [t for t in required_tools if t in tools_used]
        
        tool_selection_score = len(required_used) / max(len(required_tools), 1) if required_tools else 1.0
        tool_selection_score = min(tool_selection_score, 1.0)
        
        metrics.append(
            Metric(
                name="tool_selection",
                value=tool_selection_score,
                max_value=1.0,
                unit="ratio",
                metadata={"weight": 0.4}
            )
        )
        
        # 2. Parameter correctness (30% weight)
        param_score = 1.0
        if self.tu_config.require_correct_params and tool_calls:
            correct_calls = sum(1 for call in tool_calls if call.get("success"))
            param_score = correct_calls / len(tool_calls)
        
        metrics.append(
            Metric(
                name="parameter_correctness",
                value=param_score,
                max_value=1.0,
                unit="ratio",
                metadata={"weight": 0.3}
            )
        )
        
        # 3. Error handling (20% weight)
        error_calls = [call for call in tool_calls if not call.get("success")]
        
        # Penalize errors if configured
        error_handling_score = 1.0 - (len(error_calls) / max(len(tool_calls), 1)) * 0.5
        error_handling_score = max(error_handling_score, 0.0)
        
        metrics.append(
            Metric(
                name="error_handling",
                value=error_handling_score,
                max_value=1.0,
                unit="ratio",
                metadata={"weight": 0.2, "errors": len(error_calls)}
            )
        )
        
        # 4. Tool chain efficiency (10% weight)
        call_count = len(tool_calls)
        expected_count = len(expected_calls) if expected_calls else 1
        
        # Penalize excessive tool calls
        efficiency_score = 1.0 / (1.0 + abs(call_count - expected_count) * 0.1)
        efficiency_score = max(efficiency_score, 0.0)
        
        metrics.append(
            Metric(
                name="efficiency",
                value=efficiency_score,
                max_value=1.0,
                unit="penalty",
                metadata={"weight": 0.1, "calls": call_count}
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
            tool_selection_score >= 0.8 and
            param_score >= 0.8 and
            final_score >= 0.7
        )
        
        # Generate feedback
        feedback_parts = []
        feedback_parts.append(f"Tool selection score: {tool_selection_score*100:.1f}%.")
        feedback_parts.append(f"Parameter correctness: {param_score*100:.1f}%.")
        feedback_parts.append(f"Tool calls made: {call_count} (expected: {expected_count}).")
        
        if error_calls:
            feedback_parts.append(f"Encountered {len(error_calls)} tool execution error(s).")
        
        feedback = " ".join(feedback_parts)
        
        return final_score, passed, feedback, metrics


# Register the dimension
from agentfit.core.dimension import DimensionRegistry
DimensionRegistry.register(ToolUse)
