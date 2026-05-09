# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path

import pytest

from swe.agents import react_agent
from swe.agents import tool_guard_mixin
from swe.agents.react_agent import AgentPhase, SWEAgent
from swe.agents.tool_guard_mixin import ToolGuardMixin
from swe.agents.tools import file_io
from swe.config.context import tenant_context


def _bare_agent() -> SWEAgent:
    agent = object.__new__(SWEAgent)
    agent.name = "Friday"
    agent._request_context = {
        "session_id": "session-1",
        "user_id": "user-1",
        "agent_id": "agent-1",
    }
    agent._watchdog_task = None
    agent._reply_task = None
    agent._init_agent_phase_state()
    return agent


async def _cleanup_agent(agent: SWEAgent) -> None:
    agent._stop_watchdog()
    task = getattr(agent, "_reply_task", None)
    if task and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_reasoning_phase_silence_interrupts_agent(monkeypatch):
    agent = _bare_agent()
    agent._reply_task = asyncio.create_task(asyncio.sleep(10))
    messages: list[str] = []
    monkeypatch.setattr(
        react_agent.logger,
        "warning",
        lambda msg, *args, **kwargs: messages.append(msg % args),
    )

    try:
        with agent.agent_phase(AgentPhase.REASONING, reason="unit-test"):
            agent._start_watchdog(timeout=0.02, check_interval=0.005)
            await asyncio.sleep(0.06)

        assert agent._reply_task.cancelled()
        assert any(
            "phase=reasoning" in message and "silence_duration=" in message
            for message in messages
        )
    finally:
        await _cleanup_agent(agent)


@pytest.mark.asyncio
async def test_tool_phase_silence_within_hard_timeout_is_not_interrupted():
    agent = _bare_agent()
    agent._reply_task = asyncio.create_task(asyncio.sleep(10))

    try:
        with agent.agent_phase(
            AgentPhase.TOOL_EXECUTION,
            tool_name="slow_local_tool",
            tool_call_id="tool-call-1",
            reason="unit-test",
        ):
            agent._start_watchdog(timeout=0.02, check_interval=0.005)
            await asyncio.sleep(0.06)

        assert not agent._reply_task.done()
    finally:
        await _cleanup_agent(agent)


class _SlowToolBase:
    async def _acting(self, tool_call):
        await asyncio.sleep(0.05)
        return {"type": "tool_result", "id": tool_call["id"], "output": []}


class _SlowToolAgent(ToolGuardMixin, _SlowToolBase):
    def __init__(self) -> None:
        self.name = "Friday"
        self._request_context = {"session_id": "session-1"}
        self._tool_guard_forced_replay_active = False
        self._tool_guard_replay_queue = []


@pytest.mark.asyncio
async def test_generic_local_tool_hard_timeout_returns_tool_failure(
    monkeypatch,
):
    monkeypatch.setattr(
        tool_guard_mixin,
        "LOCAL_TOOL_EXECUTION_HARD_TIMEOUT",
        0.01,
    )
    agent = _SlowToolAgent()

    result = await agent._run_tool_call_with_hard_timeout(
        {"id": "tool-call-1", "name": "slow_local_tool", "input": {}},
        "slow_local_tool",
        {},
    )

    assert result is not None
    assert result["id"] == "tool-call-1"
    output_text = result["output"][0]["text"]
    assert "slow_local_tool" in output_text
    assert "timed out" in output_text
    assert "0.01" in output_text


@pytest.mark.asyncio
async def test_watchdog_interrupt_log_includes_phase_and_tool_metadata(
    monkeypatch,
):
    agent = _bare_agent()
    agent._reply_task = asyncio.create_task(asyncio.sleep(10))
    messages: list[str] = []
    monkeypatch.setattr(
        react_agent.logger,
        "warning",
        lambda msg, *args, **kwargs: messages.append(msg % args),
    )

    try:
        with agent.agent_phase(
            AgentPhase.UNKNOWN,
            tool_name="mystery_tool",
            tool_call_id="tool-call-2",
            reason="unit-test",
        ):
            agent._start_watchdog(timeout=0.02, check_interval=0.005)
            await asyncio.sleep(0.06)

        assert any("phase=unknown" in message for message in messages)
        assert any("tool_name=mystery_tool" in message for message in messages)
        assert any("tool_call_id=tool-call-2" in message for message in messages)
        assert any("session_id=session-1" in message for message in messages)
        assert any("agent_id=agent-1" in message for message in messages)
    finally:
        await _cleanup_agent(agent)


@pytest.mark.asyncio
async def test_file_write_diagnostics_include_size_and_timing_not_content(
    tmp_path: Path,
    monkeypatch,
):
    tenant_dir = tmp_path / "tenant_a"
    workspace_dir = tenant_dir / "workspaces" / "agent_a"
    workspace_dir.mkdir(parents=True)
    secret_content = "do-not-log-this-content"
    messages: list[str] = []

    monkeypatch.setattr(file_io, "FILE_WRITE_SLOW_WARNING_SECONDS", 0.0)
    monkeypatch.setattr(
        file_io.logger,
        "warning",
        lambda msg, *args, **kwargs: messages.append(msg % args),
    )

    with monkeypatch.context() as m:
        m.setattr("swe.security.tenant_path_boundary.WORKING_DIR", tmp_path)
        with tenant_context(tenant_id="tenant_a", workspace_dir=workspace_dir):
            await file_io.write_file("note.txt", secret_content)
            await file_io.append_file("note.txt", secret_content)

    combined = "\n".join(messages)
    assert "operation=write_file" in combined
    assert "operation=append_file" in combined
    assert "content_bytes=" in combined
    assert "total_seconds=" in combined
    assert secret_content not in combined
