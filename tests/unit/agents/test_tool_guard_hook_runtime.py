# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio

import pytest

from swe.agents.hook_runtime.models import (
    AdditionalContext,
    CommandHookHandlerConfig,
    HookConfig,
    HookDecision,
    HookEventName,
    HookHandlerResult,
    HookMatcherGroupConfig,
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


@pytest.mark.asyncio
async def test_tool_hook_once_state_is_written_back_to_request_context(
    monkeypatch,
    tmp_path,
) -> None:
    agent = _FakeAgent(tmp_path)
    tenant_hooks = HookConfig(
        enabled=True,
        events={
            HookEventName.PRE_TOOL_USE: [
                HookMatcherGroupConfig(
                    hooks=[
                        CommandHookHandlerConfig(
                            id="once",
                            command="echo {}",
                            once=True,
                        ),
                    ],
                ),
            ],
        },
    )
    calls = []

    async def fake_execute_handler(handler, context, *, workspace_dir):
        calls.append((handler.id, context.hook_event_name, workspace_dir))
        return HookHandlerResult(handler_id=handler.id, order=0)

    monkeypatch.setattr(
        "swe.agents.tool_guard_mixin.ToolGuardMixin._load_tenant_hook_config",
        lambda self: tenant_hooks,
    )
    monkeypatch.setattr(
        "swe.agents.hook_runtime.runtime.execute_handler",
        fake_execute_handler,
    )

    await agent._emit_tool_hook(
        HookEventName.PRE_TOOL_USE,
        tool_name="execute_shell_command",
        tool_input={"cmd": "echo one"},
        tool_use_id="tool-1",
    )
    await agent._emit_tool_hook(
        HookEventName.PRE_TOOL_USE,
        tool_name="execute_shell_command",
        tool_input={"cmd": "echo two"},
        tool_use_id="tool-2",
    )

    assert [call[0] for call in calls] == ["once"]
    hook_overlay = agent._request_context["hook_overlay"]
    assert isinstance(hook_overlay, dict)
    once_executed = hook_overlay["once_executed"]
    assert once_executed == {
        "default:user-1:session-1:PreToolUse:once": True,
    }
