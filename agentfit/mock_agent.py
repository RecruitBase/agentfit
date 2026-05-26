"""
Mock Agent for Testing.

A deterministic, configurable mock agent for testing the evaluation
pipeline without a real LLM endpoint.

Key improvements over the original:
  - Seeded RNG for fully reproducible results across runs
  - Behavior modes: realistic | always_succeed | always_fail | scripted
  - Async execute() compatible with UniversalAgentProtocol dimensions
  - to_agent_interface() now returns an async callable
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
import asyncio
import random
import time


@dataclass
class AgentStep:
    """One step in a mock agent execution."""

    step_num: int
    action: str
    tool_used: Optional[str] = None
    input_params: Dict[str, Any] = field(default_factory=dict)
    output: Optional[str] = None
    success: bool = True
    reasoning: str = ""


@dataclass
class AgentExecution:
    """Result of a mock agent run."""

    task_id: str
    steps: List[AgentStep]
    total_steps: int
    final_output: Optional[str]
    success: bool
    execution_time_ms: float
    errors: List[str]
    tools_used: List[str]

    # Dimension-compatible accessors so AgentExecution works wherever
    # a dict with these keys is expected.
    def to_dimension_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "steps": [{"action": s.action, "tool": s.tool_used} for s in self.steps],
            "tools_used": self.tools_used,
            "output": self.final_output or "",
            "errors": self.errors,
            "attempts": 1,
        }


class MockAgent:
    """
    Configurable mock agent for evaluation pipeline testing.

    Behavior modes
    --------------
    "realistic"      — Each step succeeds with probability *success_rate*.
                       Reproducible when *seed* is set.
    "always_succeed" — Every step and task succeeds regardless of success_rate.
    "always_fail"    — Every step and task fails.
    "scripted"       — Plays back a pre-defined list of step outcomes supplied
                       via the *script* parameter.

    Scripted example::

        script = [
            {"action": "lookup customer", "tool": "crm", "success": True},
            {"action": "process refund",  "tool": "billing", "success": False},
        ]
        agent = MockAgent(behavior="scripted", script=script)
    """

    BEHAVIORS = ("realistic", "always_succeed", "always_fail", "scripted")

    def __init__(
        self,
        agent_id: str = "mock-agent-001",
        success_rate: float = 0.8,
        seed: Optional[int] = None,
        behavior: str = "realistic",
        script: Optional[List[Dict[str, Any]]] = None,
    ):
        if behavior not in self.BEHAVIORS:
            raise ValueError(f"behavior must be one of {self.BEHAVIORS}, got '{behavior}'")
        if behavior == "scripted" and not script:
            raise ValueError("behavior='scripted' requires a non-empty script list")

        self.agent_id = agent_id
        self.success_rate = success_rate
        self.behavior = behavior
        self.script = script or []
        self._rng = random.Random(seed)  # seeded → deterministic

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def execute(
        self,
        task: str,
        scenario: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentExecution:
        """Execute a mock task. Returns AgentExecution (sync)."""
        t0 = time.time()

        task_id = scenario.get("id", f"mock-{self._rng.randint(1000, 9999)}")
        expected_steps: List[str] = scenario.get("expected_steps", [])
        expected_tools: List[str] = scenario.get("expected_tools", [])

        steps: List[AgentStep] = []
        tools_used: List[str] = []
        errors: List[str] = []

        script_iter = iter(self.script)

        for i, step_desc in enumerate(expected_steps, 1):
            step_success, tool = self._resolve_step(i, script_iter, expected_tools)

            if tool:
                tools_used.append(tool)

            step = AgentStep(
                step_num=i,
                action=step_desc,
                tool_used=tool,
                input_params={"query": task[:50]},
                output=f"Step {i} result: {step_desc}" if step_success else None,
                success=step_success,
                reasoning=f"Executing step {i}",
            )
            steps.append(step)

            if not step_success:
                errors.append(f"Step {i} failed: {step_desc}")

        success_count = sum(1 for s in steps if s.success)
        overall = (
            success_count / max(len(steps), 1) >= self.success_rate
            if steps
            else True
        )

        return AgentExecution(
            task_id=task_id,
            steps=steps,
            total_steps=len(steps),
            final_output=task if overall else None,
            success=overall,
            execution_time_ms=(time.time() - t0) * 1000,
            errors=errors,
            tools_used=list(dict.fromkeys(tools_used)),  # deduplicate, preserve order
        )

    def _resolve_step(
        self,
        step_num: int,
        script_iter,
        expected_tools: List[str],
    ):
        """Return (step_success, tool_used) for a single step."""
        if self.behavior == "always_succeed":
            success = True
        elif self.behavior == "always_fail":
            success = False
        elif self.behavior == "scripted":
            entry = next(script_iter, {})
            success = entry.get("success", True)
            tool = entry.get("tool", None)
            return success, tool
        else:  # realistic
            success = self._rng.random() < self.success_rate

        tool = None
        if expected_tools and self._rng.random() < 0.7:
            tool = self._rng.choice(expected_tools)

        return success, tool

    # ------------------------------------------------------------------
    # Async execute — dimension-compatible
    # ------------------------------------------------------------------

    async def async_execute(
        self,
        task: str,
        expected_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Async execute wrapper returning the dimension-compatible dict format:
          {"success", "steps", "tools_used", "output", "errors", "attempts"}
        """
        scenario = {
            "id": f"mock-async-{self._rng.randint(1000, 9999)}",
            "task": task,
            "expected_steps": [f"step_{i}" for i in range(1, 4)],
            "expected_tools": expected_tools or [],
        }
        result = self.execute(task=task, scenario=scenario, context=context)
        return result.to_dimension_dict()

    # Alias so UAP dimensions that call agent.execute() work transparently
    execute_async = async_execute

    # ------------------------------------------------------------------
    # Interface adapters
    # ------------------------------------------------------------------

    def to_agent_interface(self) -> Callable:
        """
        Return an *async* callable compatible with EvaluationRequest.agent_interface.

        The callable signature matches what dimensions expect:
            result = await agent_interface(scenario, context)

        The returned dict has keys: success, steps, tools_used, output,
        errors, attempts.
        """
        async def _call(scenario: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
            if isinstance(scenario, dict):
                task = scenario.get("task", "")
                scenario_dict = scenario
            else:
                task = str(scenario)
                scenario_dict = {"task": task}
            exec_result = self.execute(task=task, scenario=scenario_dict, context=context)
            return exec_result.to_dimension_dict()

        return _call
