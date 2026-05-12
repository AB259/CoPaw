# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio

import pytest

from swe.agents.hook_runtime.models import (
    AdditionalContext,
    HookDecision,
    MergedHookResult,
)
from swe.agents.tool_guard_mixin import ToolGuardMixin


class _Memory:
    def __init__(self):
        self.content = []

    async def add(self, msg, marks=None):
        self.content.append((msg, marks))


class _BaseAgent:
    async def _acting(self, tool_call):
        return {"content": tool_call["input"]}


class _FakeAgent(ToolGuardMixin, _BaseAgent):
    name = "Friday"

    def __init__(self, tmp_path: Path):
        self._request_context = {
            "session_id": "session-1",
            "user_id": "user-1",
            "channel": "console",
            "agent_id": "agent-1",
        }
        self._agent_config = SimpleNamespace()
        self._workspace_dir = tmp_path
        self.memory = _Memory()
        self.printed = []
        self._tool_guard_lock = asyncio.Lock()

    def _ensure_tool_guard(self) -> None:
        self._tool_guard_engine = SimpleNamespace(enabled=False)

    async def print(self, msg, *args, **kwargs):
        self.printed.append(msg)


@pytest.mark.asyncio
async def test_no_hook_config_preserves_tool_execution(tmp_path) -> None:
    agent = _FakeAgent(tmp_path)

    result = await agent._acting(
        {
            "id": "tool-1",
            "name": "read_file",
            "input": {"path": "README.md"},
        },
    )

    assert result == {"content": {"path": "README.md"}}
    assert agent.memory.content == []


@pytest.mark.asyncio
async def test_pre_tool_hook_updated_input_replaces_tool_call(
    tmp_path,
) -> None:
    agent = _FakeAgent(tmp_path)
    agent._emit_tool_hook = AsyncMock(
        side_effect=[
            MergedHookResult(updated_input={"cmd": "echo replaced"}),
            MergedHookResult(),
        ],
    )

    result = await agent._acting(
        {
            "id": "tool-1",
            "name": "execute_shell_command",
            "input": {"cmd": "echo original"},
        },
    )

    assert result == {"content": {"cmd": "echo replaced"}}


@pytest.mark.asyncio
async def test_pre_tool_hook_denial_returns_tool_result(tmp_path) -> None:
    agent = _FakeAgent(tmp_path)
    agent._emit_tool_hook = AsyncMock(
        return_value=MergedHookResult(
            decision=HookDecision.DENY,
            reason="no shell",
        ),
    )

    result = await agent._acting(
        {
            "id": "tool-1",
            "name": "execute_shell_command",
            "input": {"cmd": "echo original"},
        },
    )

    assert result is None
    assert "no shell" in str(agent.printed[0].content)


@pytest.mark.asyncio
async def test_pre_tool_hook_ask_uses_existing_approval_path(tmp_path) -> None:
    agent = _FakeAgent(tmp_path)
    agent._emit_tool_hook = AsyncMock(
        return_value=MergedHookResult(
            decision=HookDecision.ASK,
            reason="review shell",
        ),
    )
    agent._acting_with_approval = AsyncMock(return_value=None)

    await agent._acting(
        {
            "id": "tool-1",
            "name": "execute_shell_command",
            "input": {"cmd": "echo original"},
        },
    )

    agent._acting_with_approval.assert_awaited_once()
    guard_result = agent._acting_with_approval.await_args.args[2]
    assert guard_result.findings[0].guardian == "unified_hook_runtime"


@pytest.mark.asyncio
async def test_post_tool_hook_additional_context_is_added_to_memory(
    tmp_path,
) -> None:
    agent = _FakeAgent(tmp_path)
    agent._emit_tool_hook = AsyncMock(
        side_effect=[
            MergedHookResult(),
            MergedHookResult(
                additional_context=[
                    AdditionalContext(
                        handler_id="post",
                        context="remember me",
                    ),
                ],
            ),
        ],
    )

    await agent._acting(
        {
            "id": "tool-1",
            "name": "read_file",
            "input": {"path": "README.md"},
        },
    )

    assert "remember me" in agent.memory.content[-1][0].content


@pytest.mark.asyncio
async def test_tool_failure_hook_block_reason_is_added_to_memory(
    tmp_path,
) -> None:
    agent = _FakeAgent(tmp_path)
    agent._run_tool_call_with_hard_timeout = AsyncMock(
        side_effect=RuntimeError("tool failed"),
    )
    agent._emit_tool_hook = AsyncMock(
        side_effect=[
            MergedHookResult(),
            MergedHookResult(
                decision=HookDecision.BLOCK,
                reason="failure context",
            ),
        ],
    )

    with pytest.raises(RuntimeError):
        await agent._acting(
            {
                "id": "tool-1",
                "name": "read_file",
                "input": {"path": "README.md"},
            },
        )

    assert "failure context" in agent.memory.content[-1][0].content
