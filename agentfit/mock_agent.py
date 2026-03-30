"""
Mock Agent for Testing.

A simple mock agent that simulates execution based on test scenarios.
Used for testing the evaluation pipeline without real agent implementations.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import random
from datetime import datetime


@dataclass
class AgentStep:
    """Represents a step in agent execution."""
    step_num: int
    action: str
    tool_used: Optional[str] = None
    input_params: Dict[str, Any] = None
    output: Optional[str] = None
    success: bool = True
    reasoning: str = ""
    
    def __post_init__(self):
        if self.input_params is None:
            self.input_params = {}


@dataclass
class AgentExecution:
    """Result of mock agent execution."""
    task_id: str
    steps: List[AgentStep]
    total_steps: int
    final_output: Optional[str]
    success: bool
    execution_time_ms: float
    errors: List[str]
    tools_used: List[str]


class MockAgent:
    """Mock agent that simulates task execution."""
    
    def __init__(self, agent_id: str = "mock-agent-001", success_rate: float = 0.8):
        """Initialize mock agent.
        
        Args:
            agent_id: Identifier for the agent
            success_rate: Probability of successful execution (0-1)
        """
        self.agent_id = agent_id
        self.success_rate = success_rate
    
    def execute(
        self,
        task: str,
        scenario: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentExecution:
        """Execute a mock task based on scenario.
        
        Args:
            task: Task description
            scenario: Test scenario with expected steps and tools
            context: Additional execution context
            
        Returns:
            AgentExecution with simulated results
        """
        import time
        start_time = time.time()
        
        task_id = scenario.get("id", "task-" + str(random.randint(1000, 9999)))
        expected_steps = scenario.get("expected_steps", [])
        expected_tools = scenario.get("expected_tools", [])
        
        steps = []
        tools_used = []
        errors = []
        
        # Simulate execution steps
        for i, step_desc in enumerate(expected_steps, 1):
            # Randomly decide if this step succeeds
            step_success = random.random() < self.success_rate
            
            # Select a random tool if available
            tool = None
            if expected_tools and random.random() < 0.7:  # 70% chance to use a tool
                tool = random.choice(expected_tools)
                tools_used.append(tool)
            
            step = AgentStep(
                step_num=i,
                action=step_desc,
                tool_used=tool,
                input_params={"query": task[:50] + "..." if len(task) > 50 else task},
                output=f"Result from step {i}: {step_desc}",
                success=step_success,
                reasoning=f"Executing step {i} based on task requirements"
            )
            steps.append(step)
            
            if not step_success:
                errors.append(f"Step {i} failed: {step_desc}")
        
        # Overall success depends on success_rate and whether majority of steps passed
        success_count = sum(1 for s in steps if s.success)
        overall_success = success_count / max(len(steps), 1) >= self.success_rate
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return AgentExecution(
            task_id=task_id,
            steps=steps,
            total_steps=len(steps),
            final_output=task if overall_success else None,
            success=overall_success,
            execution_time_ms=execution_time_ms,
            errors=errors,
            tools_used=list(set(tools_used))  # Remove duplicates
        )
    
    def to_agent_interface(self) -> callable:
        """Return a callable interface compatible with Evaluator.
        
        Returns:
            Callable that matches agent_interface signature
        """
        def agent_call(scenario: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentExecution:
            return self.execute(
                task=scenario.get("task", ""),
                scenario=scenario,
                context=context
            )
        
        return agent_call
