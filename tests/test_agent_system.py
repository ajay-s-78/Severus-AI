import pytest
import asyncio
from app.services.agents import agent_system, BaseAgent, AgentResult


@pytest.mark.anyio
async def test_general_agent_execution():
    res = await agent_system.execute_agent_workflow("general", {"message": "Hello Severus"})
    assert res.success is True
    assert res.agent_name == "GeneralAgent"


@pytest.mark.anyio
async def test_computer_control_security_boundary_unauthorized():
    res = await agent_system.execute_agent_workflow(
        "computer_control",
        {"action_type": "open_app", "target": "calc", "speaker_status": "UNAUTHORIZED_SPEAKER"}
    )
    assert res.success is False
    assert res.data["blocked"] is True
    assert "restricted" in res.message.lower() or "only authorized_owner" in res.message.lower()


@pytest.mark.anyio
async def test_computer_control_security_boundary_authorized():
    res = await agent_system.execute_agent_workflow(
        "computer_control",
        {"action_type": "open_app", "target": "calc", "speaker_status": "AUTHORIZED_OWNER"}
    )
    assert res.success is True
    assert "action_required" in res.data


@pytest.mark.anyio
async def test_memory_security_boundary_unauthorized():
    res = await agent_system.execute_agent_workflow(
        "memory",
        {"speaker_status": "UNAUTHORIZED_SPEAKER"}
    )
    assert res.success is False
    assert res.data["blocked"] is True


@pytest.mark.anyio
async def test_tool_timeout_handing():
    class SlowTestAgent(BaseAgent):
        def __init__(self):
            super().__init__("SlowAgent", "Slow test agent")

        async def execute(self, task_input, context=None):
            await asyncio.sleep(2.0)
            return AgentResult(agent_name=self.name, success=True, data={}, message="Done")

    agent_system.agents["slow_test"] = SlowTestAgent()

    # Execute with 0.1s timeout to verify graceful timeout handling
    res = await agent_system.execute_agent_workflow("slow_test", {}, max_retries=1, timeout_seconds=0.1)
    assert res.success is False
    assert res.data.get("error") == "timeout" or "timed out" in res.message


@pytest.mark.anyio
async def test_retry_limit_and_recovery():
    attempts = 0

    class FlakyAgent(BaseAgent):
        def __init__(self):
            super().__init__("FlakyAgent", "Flaky agent")

        async def execute(self, task_input, context=None):
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("Transient error")
            return AgentResult(agent_name=self.name, success=True, data={"recovered": True}, message="Recovered")

    agent_system.agents["flaky_test"] = FlakyAgent()
    res = await agent_system.execute_agent_workflow("flaky_test", {}, max_retries=3, timeout_seconds=2.0)
    assert res.success is True
    assert res.steps_taken == 2
