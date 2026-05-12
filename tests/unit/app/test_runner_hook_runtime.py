# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agentscope.message import Msg

from swe.agents.hook_runtime.models import (
    CommandHookHandlerConfig,
    HookConfig,
    HookDecision,
    HookEventName,
    HookMatcherGroupConfig,
    AdditionalContext,
    MergedHookResult,
)
from swe.app.runner.runner import AgentRunner
from swe.app.runner.session import SafeJSONSession
from swe.config.config import SuggestionMode


def _agent_config(hooks: HookConfig | None = None):
    return SimpleNamespace(
        id="test-agent",
        hooks=hooks or HookConfig(),
        mcp=None,
        running=SimpleNamespace(
            suggestions=SimpleNamespace(
                enabled=False,
                mode=SuggestionMode.DISABLED,
            ),
            post_turn_validation=SimpleNamespace(enabled=False),
        ),
    )


class _FakeAgent:
    last_env_context = ""

    def __init__(self, **kwargs):
        self.memory = SimpleNamespace(content=[])
        self.env_context = kwargs.get("env_context", "")
        _FakeAgent.last_env_context = self.env_context

    async def register_mcp_clients(self):
        return

    def set_console_output_enabled(self, enabled=False):
        del enabled

    def rebuild_sys_prompt(self):
        return

    async def __call__(self, turn_msgs):
        for msg in turn_msgs:
            self.memory.content.append((msg, []))
        reply = Msg(name="Friday", role="assistant", content="agent reply")
        self.memory.content.append((reply, []))
        return [reply]

    def state_dict(self):
        return {
            "memory": {
                "content": [
                    [msg.to_dict(), marks]
                    for msg, marks in self.memory.content
                ],
            },
        }


async def _fake_stream_printing_messages(*, agents, coroutine_task):
    del agents
    turn_msgs = await coroutine_task
    for msg in turn_msgs:
        yield msg, True


def _patch_normal_agent_path(monkeypatch):
    monkeypatch.setattr(
        "swe.app.runner.runner._build_and_connect_mcp_clients",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr("swe.app.runner.runner.SWEAgent", _FakeAgent)
    monkeypatch.setattr(
        "swe.app.runner.runner.stream_printing_messages",
        _fake_stream_printing_messages,
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._cleanup_mcp_clients",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner.build_env_context",
        lambda **kwargs: "base context",
    )


@pytest.mark.asyncio
async def test_query_handler_user_prompt_hook_blocks_before_command_dispatch(
    monkeypatch,
    tmp_path,
) -> None:
    runner = AgentRunner(agent_id="test-agent", workspace_dir=tmp_path)
    runner.session = SimpleNamespace(
        get_session_state_dict=AsyncMock(return_value={}),
    )
    setattr(runner, "_chat_manager", None)
    tenant_hooks = HookConfig(
        enabled=True,
        events={
            HookEventName.USER_PROMPT_SUBMIT: [
                HookMatcherGroupConfig(
                    hooks=[
                        CommandHookHandlerConfig(
                            id="blocker",
                            command="unused",
                        ),
                    ],
                ),
            ],
        },
    )

    monkeypatch.setattr(
        "swe.app.runner.runner.load_agent_config",
        lambda *args, **kwargs: _agent_config(),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._load_tenant_hook_config",
        lambda *args, **kwargs: tenant_hooks,
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._emit_runner_hook",
        AsyncMock(
            return_value=MergedHookResult(
                decision=HookDecision.BLOCK,
                reason="blocked prompt",
            ),
        ),
    )
    command_path = AsyncMock()
    monkeypatch.setattr("swe.app.runner.runner.run_command_path", command_path)

    request = SimpleNamespace(
        session_id="session-1",
        user_id="user-1",
        channel="console",
        channel_meta={},
    )
    msgs = [Msg(name="user", role="user", content="/history")]

    outputs = [
        item async for item in runner.query_handler(msgs, request=request)
    ]

    assert outputs[-1][1] is True
    assert "blocked prompt" in outputs[-1][0].get_text_content()
    command_path.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_handler_no_config_does_not_emit_hook(
    monkeypatch,
    tmp_path,
) -> None:
    runner = AgentRunner(agent_id="test-agent", workspace_dir=tmp_path)
    runner.session = SimpleNamespace(
        get_session_state_dict=AsyncMock(return_value={}),
    )
    setattr(runner, "_chat_manager", None)

    monkeypatch.setattr(
        "swe.app.runner.runner.load_agent_config",
        lambda *args, **kwargs: _agent_config(),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._load_tenant_hook_config",
        lambda *args, **kwargs: HookConfig(),
    )
    emit_hook = AsyncMock(return_value=MergedHookResult())
    monkeypatch.setattr("swe.app.runner.runner._emit_runner_hook", emit_hook)

    async def fake_run_command_path(request, msgs, runner):
        yield Msg(name="Friday", role="assistant", content="command"), True

    monkeypatch.setattr(
        "swe.app.runner.runner.run_command_path",
        fake_run_command_path,
    )

    request = SimpleNamespace(
        session_id="session-1",
        user_id="user-1",
        channel="console",
        channel_meta={},
    )
    msgs = [Msg(name="user", role="user", content="/history")]

    outputs = [
        item async for item in runner.query_handler(msgs, request=request)
    ]

    assert outputs[-1][0].get_text_content() == "command"
    emit_hook.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_handler_injects_prompt_additional_context(
    monkeypatch,
    tmp_path,
) -> None:
    runner = AgentRunner(agent_id="test-agent", workspace_dir=tmp_path)
    runner.session = SafeJSONSession(save_dir=str(tmp_path))
    setattr(runner, "_chat_manager", None)
    _patch_normal_agent_path(monkeypatch)
    monkeypatch.setattr(
        "swe.app.runner.runner.load_agent_config",
        lambda *args, **kwargs: _agent_config(HookConfig(enabled=True)),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._load_tenant_hook_config",
        lambda *args, **kwargs: HookConfig(enabled=True),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._resolve_active_model_label",
        lambda *args, **kwargs: "openai/gpt-test",
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._emit_runner_hook",
        AsyncMock(
            side_effect=[
                MergedHookResult(
                    session_title="Hooked",
                    additional_context=[
                        AdditionalContext(
                            handler_id="prompt",
                            context="prompt context",
                        ),
                    ],
                ),
                MergedHookResult(
                    additional_context=[
                        AdditionalContext(
                            handler_id="start",
                            context="start context",
                        ),
                    ],
                ),
                MergedHookResult(),
            ],
        ),
    )

    request = SimpleNamespace(
        session_id="session-1",
        user_id="user-1",
        channel="console",
        channel_meta={},
    )
    msgs = [Msg(name="user", role="user", content="hello")]

    outputs = [
        item async for item in runner.query_handler(msgs, request=request)
    ]

    assert outputs[-1][0].get_text_content() == "agent reply"
    assert request.channel_meta["session_title"] == "Hooked"
    assert "prompt context" in _FakeAgent.last_env_context
    assert "start context" in _FakeAgent.last_env_context


@pytest.mark.asyncio
async def test_query_handler_stop_hook_blocks_completion(
    monkeypatch,
    tmp_path,
) -> None:
    runner = AgentRunner(agent_id="test-agent", workspace_dir=tmp_path)
    runner.session = SafeJSONSession(save_dir=str(tmp_path))
    setattr(runner, "_chat_manager", None)
    _patch_normal_agent_path(monkeypatch)
    monkeypatch.setattr(
        "swe.app.runner.runner.load_agent_config",
        lambda *args, **kwargs: _agent_config(HookConfig(enabled=True)),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._load_tenant_hook_config",
        lambda *args, **kwargs: HookConfig(enabled=True),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._emit_runner_hook",
        AsyncMock(
            side_effect=[
                MergedHookResult(),
                MergedHookResult(),
                MergedHookResult(
                    decision=HookDecision.BLOCK,
                    reason="stop blocked",
                ),
            ],
        ),
    )

    request = SimpleNamespace(
        session_id="session-1",
        user_id="user-1",
        channel="console",
        channel_meta={},
    )
    msgs = [Msg(name="user", role="user", content="hello")]

    outputs = [
        item async for item in runner.query_handler(msgs, request=request)
    ]

    assert [item[0].get_text_content() for item in outputs] == [
        "agent reply",
        "stop blocked",
    ]


@pytest.mark.asyncio
async def test_query_handler_persists_mutated_hook_overlay(
    monkeypatch,
    tmp_path,
) -> None:
    runner = AgentRunner(agent_id="test-agent", workspace_dir=tmp_path)
    runner.session = SafeJSONSession(save_dir=str(tmp_path))
    setattr(runner, "_chat_manager", None)
    _patch_normal_agent_path(monkeypatch)
    monkeypatch.setattr(
        "swe.app.runner.runner.load_agent_config",
        lambda *args, **kwargs: _agent_config(HookConfig(enabled=True)),
    )
    monkeypatch.setattr(
        "swe.app.runner.runner._load_tenant_hook_config",
        lambda *args, **kwargs: HookConfig(enabled=True),
    )

    async def fake_emit_runner_hook(*args, **kwargs):
        kwargs["overlay"].once_executed[
            "default:user-1:session-1:PreToolUse:once"
        ] = True
        return MergedHookResult()

    monkeypatch.setattr(
        "swe.app.runner.runner._emit_runner_hook",
        fake_emit_runner_hook,
    )

    request = SimpleNamespace(
        session_id="session-1",
        user_id="user-1",
        channel="console",
        channel_meta={},
    )
    msgs = [Msg(name="user", role="user", content="hello")]

    outputs = [
        item async for item in runner.query_handler(msgs, request=request)
    ]
    state = await runner.session.get_session_state_dict(
        session_id="session-1",
        user_id="user-1",
    )

    assert outputs[-1][0].get_text_content() == "agent reply"
    assert state["hook_overlay"]["once_executed"] == {
        "default:user-1:session-1:PreToolUse:once": True,
    }
