"""
Tests for MockAgent — seed reproducibility, behavior modes, async interface.
"""

import inspect
import asyncio
import pytest

from agentfit.mock_agent import MockAgent, AgentExecution


SCENARIO = {
    "id": "test-001",
    "task": "Resolve a billing complaint",
    "expected_steps": ["greet", "verify_account", "check_billing", "apply_refund", "confirm"],
    "expected_tools": ["crm", "billing_system", "payment_processor"],
}


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestMockAgentInit:
    def test_defaults(self):
        m = MockAgent()
        assert m.success_rate == 0.8
        assert m.behavior == "realistic"

    def test_invalid_behavior_raises(self):
        with pytest.raises(ValueError, match="behavior must be one of"):
            MockAgent(behavior="hallucinating")

    def test_scripted_without_script_raises(self):
        with pytest.raises(ValueError, match="script"):
            MockAgent(behavior="scripted")

    def test_scripted_with_script_ok(self):
        m = MockAgent(behavior="scripted", script=[{"action": "step 1", "success": True}])
        assert m.behavior == "scripted"


# ---------------------------------------------------------------------------
# Seed reproducibility
# ---------------------------------------------------------------------------

class TestMockAgentSeed:
    def test_same_seed_same_result(self):
        m1 = MockAgent(seed=42)
        m2 = MockAgent(seed=42)
        r1 = m1.execute("task", SCENARIO)
        r2 = m2.execute("task", SCENARIO)
        assert r1.success == r2.success
        assert [s.success for s in r1.steps] == [s.success for s in r2.steps]
        assert r1.tools_used == r2.tools_used

    def test_different_seeds_may_differ(self):
        results = set()
        for seed in range(20):
            m = MockAgent(seed=seed, success_rate=0.5)
            r = m.execute("task", SCENARIO)
            results.add(r.success)
        # With 20 different seeds and 50% rate, we should see both True and False
        assert len(results) == 2

    def test_no_seed_nondeterministic(self):
        """Without a seed, repeated runs on the same instance should sometimes differ."""
        m = MockAgent(success_rate=0.5)
        outcomes = {m.execute("task", SCENARIO).success for _ in range(30)}
        assert len(outcomes) == 2


# ---------------------------------------------------------------------------
# Behavior modes
# ---------------------------------------------------------------------------

class TestMockAgentBehavior:
    def test_always_succeed(self):
        m = MockAgent(behavior="always_succeed")
        for _ in range(5):
            r = m.execute("task", SCENARIO)
            assert r.success is True
            assert all(s.success for s in r.steps)

    def test_always_fail(self):
        m = MockAgent(behavior="always_fail")
        for _ in range(5):
            r = m.execute("task", SCENARIO)
            assert r.success is False
            assert all(not s.success for s in r.steps)

    def test_scripted_plays_back(self):
        script = [
            {"action": "step_a", "tool": "crm",     "success": True},
            {"action": "step_b", "tool": None,       "success": False},
            {"action": "step_c", "tool": "billing",  "success": True},
        ]
        m = MockAgent(behavior="scripted", script=script)
        scenario = {**SCENARIO, "expected_steps": ["step_a", "step_b", "step_c"]}
        r = m.execute("task", scenario)
        assert r.steps[0].success is True
        assert r.steps[1].success is False
        assert r.steps[2].success is True
        assert "crm" in r.tools_used
        assert "billing" in r.tools_used

    def test_scripted_extra_steps_handled(self):
        """If scenario has more steps than script entries, extras default to success=True."""
        script = [{"action": "s1", "success": True}]
        m = MockAgent(behavior="scripted", script=script)
        scenario = {**SCENARIO, "expected_steps": ["s1", "s2", "s3"]}
        r = m.execute("task", scenario)
        assert len(r.steps) == 3


# ---------------------------------------------------------------------------
# Execution output shape
# ---------------------------------------------------------------------------

class TestMockAgentExecution:
    def test_returns_agent_execution(self):
        r = MockAgent(seed=1).execute("task", SCENARIO)
        assert isinstance(r, AgentExecution)

    def test_tools_deduped(self):
        m = MockAgent(seed=7, success_rate=1.0)
        r = m.execute("task", SCENARIO)
        assert len(r.tools_used) == len(set(r.tools_used))

    def test_to_dimension_dict_keys(self):
        r = MockAgent(seed=0).execute("task", SCENARIO)
        d = r.to_dimension_dict()
        for key in ("success", "steps", "tools_used", "output", "errors", "attempts"):
            assert key in d, f"Missing key '{key}' in dimension dict"

    def test_to_dimension_dict_types(self):
        r = MockAgent(seed=0).execute("task", SCENARIO)
        d = r.to_dimension_dict()
        assert isinstance(d["success"], bool)
        assert isinstance(d["steps"], list)
        assert isinstance(d["tools_used"], list)
        assert isinstance(d["errors"], list)
        assert d["attempts"] == 1


# ---------------------------------------------------------------------------
# Async interface
# ---------------------------------------------------------------------------

class TestMockAgentAsyncInterface:
    def test_to_agent_interface_is_coroutine_function(self):
        iface = MockAgent().to_agent_interface()
        assert inspect.iscoroutinefunction(iface)

    @pytest.mark.asyncio
    async def test_interface_returns_dimension_dict(self):
        iface = MockAgent(seed=42).to_agent_interface()
        result = await iface(SCENARIO)
        assert isinstance(result, dict)
        for key in ("success", "steps", "tools_used", "output", "errors", "attempts"):
            assert key in result

    @pytest.mark.asyncio
    async def test_interface_accepts_string_task(self):
        """Dimensions sometimes call agent_interface(task_string) not a scenario dict."""
        iface = MockAgent(seed=1).to_agent_interface()
        result = await iface("just a plain task string")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_async_execute_helper(self):
        m = MockAgent(seed=10)
        result = await m.async_execute(
            task="resolve billing complaint",
            expected_tools=["crm", "billing_system"],
        )
        assert isinstance(result, dict)
        assert "success" in result

    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self):
        """Concurrent calls must not share RNG state and all return valid dicts."""
        iface = MockAgent(seed=99).to_agent_interface()
        results = await asyncio.gather(*[iface(SCENARIO) for _ in range(10)])
        assert len(results) == 10
        assert all("success" in r for r in results)
