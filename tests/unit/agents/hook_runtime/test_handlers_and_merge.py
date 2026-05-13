# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from swe.agents.hook_runtime.executor import execute_handler
from swe.agents.hook_runtime.merge import merge_hook_results
from swe.agents.hook_runtime.models import (
    CommandHookHandlerConfig,
    EffectiveHookHandler,
    EffectiveHookPlan,
    FailPolicy,
    HookContext,
    HookDecision,
    HookEventName,
    HttpHookHandlerConfig,
)
from swe.config.context import tenant_context


def _context(event: HookEventName = HookEventName.PRE_TOOL_USE) -> HookContext:
    return HookContext(
        session_id="session-1",
        transcript_path="/tmp/transcript.json",
        cwd="/tmp/tenant-a/workspaces/default",
        hook_event_name=event,
        tenant_id="tenant-a",
        effective_tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent-1",
        channel="console",
        workspace_dir="/tmp/tenant-a/workspaces/default",
        tool_name="execute_shell_command",
        tool_input={"cmd": "echo old"},
        tool_use_id="tool-1",
    )


def _plan(*handlers) -> EffectiveHookPlan:
    return EffectiveHookPlan(
        event_name=HookEventName.PRE_TOOL_USE,
        context=_context(),
        handlers=tuple(
            EffectiveHookHandler(
                handler=h,
                group_id="group",
                order=i,
                dedupe_key=f"tenant-a:PreToolUse:group:{h.id}:{h.type}:{h.target_identity()}",
            )
            for i, h in enumerate(handlers)
        ),
    )


@pytest.mark.asyncio
async def test_command_handler_parses_exit_zero_stdout_json(
    tmp_path: Path,
) -> None:
    script = tmp_path / "hook.py"
    script.write_text(
        "import json, sys\n"
        "ctx=json.load(sys.stdin)\n"
        "print(json.dumps({'hookSpecificOutput': {'additionalContext': 'seen '+ctx['hook_event_name']}}))\n",
        encoding="utf-8",
    )
    handler = CommandHookHandlerConfig(
        id="cmd",
        argv=["python", str(script)],
    )

    with tenant_context(tenant_id="tenant-a", workspace_dir=tmp_path):
        result = await execute_handler(
            handler,
            _context(),
            workspace_dir=tmp_path,
        )

    assert result.failed is False
    assert (
        result.output.hook_specific_output["additionalContext"]
        == "seen PreToolUse"
    )


@pytest.mark.asyncio
async def test_command_exit_two_maps_to_block_without_json_parse(
    tmp_path: Path,
) -> None:
    script = tmp_path / "block.py"
    script.write_text(
        "import sys\n"
        "print('{not-json')\n"
        "print('blocked by script', file=sys.stderr)\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    handler = CommandHookHandlerConfig(
        id="blocker",
        argv=["python", str(script)],
    )

    with tenant_context(tenant_id="tenant-a", workspace_dir=tmp_path):
        result = await execute_handler(
            handler,
            _context(),
            workspace_dir=tmp_path,
        )

    assert result.failed is False
    assert result.decision == HookDecision.BLOCK
    assert "blocked by script" in result.reason


@pytest.mark.asyncio
async def test_command_cwd_escape_is_rejected(tmp_path: Path) -> None:
    handler = CommandHookHandlerConfig(
        id="escape",
        command="echo no",
        cwd=str(tmp_path.parent),
        fail_policy=FailPolicy.BLOCK,
    )

    with tenant_context(tenant_id="tenant-a", workspace_dir=tmp_path):
        result = await execute_handler(
            handler,
            _context(),
            workspace_dir=tmp_path,
        )

    assert result.failed is True
    assert result.decision == HookDecision.BLOCK
    assert "outside tenant workspace" in result.reason


@pytest.mark.asyncio
async def test_command_argv_executable_escape_is_rejected(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside-hook"
    outside.write_text("#!/bin/sh\n", encoding="utf-8")
    handler = CommandHookHandlerConfig(
        id="escape",
        argv=[str(outside)],
        fail_policy=FailPolicy.BLOCK,
    )

    result = await execute_handler(
        handler,
        _context(),
        workspace_dir=tmp_path,
    )

    assert result.failed is True
    assert result.decision == HookDecision.BLOCK
    assert "outside tenant workspace" in result.reason


@pytest.mark.asyncio
async def test_command_argv_nonexistent_absolute_escape_is_rejected(
    tmp_path: Path,
) -> None:
    handler = CommandHookHandlerConfig(
        id="escape",
        argv=["python", str(tmp_path.parent / "missing.py")],
        fail_policy=FailPolicy.BLOCK,
    )

    result = await execute_handler(
        handler,
        _context(),
        workspace_dir=tmp_path,
    )

    assert result.failed is True
    assert result.decision == HookDecision.BLOCK
    assert "outside tenant workspace" in result.reason


@pytest.mark.asyncio
async def test_command_shell_path_escape_is_rejected(tmp_path: Path) -> None:
    handler = CommandHookHandlerConfig(
        id="escape",
        command=f"cat {tmp_path.parent / 'secret.txt'}",
        fail_policy=FailPolicy.BLOCK,
    )

    result = await execute_handler(
        handler,
        _context(),
        workspace_dir=tmp_path,
    )

    assert result.failed is True
    assert result.decision == HookDecision.BLOCK
    assert "outside the allowed workspace" in result.reason


@pytest.mark.asyncio
async def test_command_shell_field_selects_requested_shell(
    monkeypatch,
    tmp_path: Path,
) -> None:
    observed = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self, payload):
            del payload
            return b"{}", b""

    async def fake_create_subprocess_shell(*args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(
        "swe.agents.hook_runtime.executor.asyncio.create_subprocess_shell",
        fake_create_subprocess_shell,
    )
    monkeypatch.setattr(
        "swe.agents.hook_runtime.executor.shutil.which",
        lambda shell: f"/tenant/bin/{shell}",
    )
    handler = CommandHookHandlerConfig(
        id="shell",
        command="echo {}",
        shell="bash",
    )

    result = await execute_handler(
        handler,
        _context(),
        workspace_dir=tmp_path,
    )

    assert result.failed is False
    assert observed["kwargs"]["executable"] == "/tenant/bin/bash"


@pytest.mark.asyncio
async def test_http_handler_maps_2xx_json_and_409_block(monkeypatch) -> None:
    responses = [
        httpx.Response(
            200,
            json={
                "hookSpecificOutput": {
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "ok",
                },
            },
        ),
        httpx.Response(409, text="blocked remotely"),
    ]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return responses.pop(0)

    monkeypatch.setattr(
        "swe.agents.hook_runtime.executor.httpx.AsyncClient",
        FakeClient,
    )

    allow = await execute_handler(
        HttpHookHandlerConfig(id="http-allow", url="https://hooks.example/a"),
        _context(),
        workspace_dir=Path("/tmp/tenant-a/workspaces/default"),
    )
    block = await execute_handler(
        HttpHookHandlerConfig(id="http-block", url="https://hooks.example/b"),
        _context(),
        workspace_dir=Path("/tmp/tenant-a/workspaces/default"),
    )

    assert allow.decision == HookDecision.ALLOW
    assert allow.reason == "ok"
    assert block.decision == HookDecision.BLOCK
    assert "blocked remotely" in block.reason


@pytest.mark.asyncio
async def test_http_handler_resolves_header_secret_from_effective_tenant(
    monkeypatch,
) -> None:
    observed = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            observed.update(kwargs.get("headers") or {})
            return httpx.Response(200, json={})

    monkeypatch.setattr(
        "swe.agents.hook_runtime.executor.httpx.AsyncClient",
        FakeClient,
    )
    tenant_calls = []

    def fake_get_tenant_env(key, tenant_id=None, default=None):
        tenant_calls.append((key, tenant_id))
        return "tenant-secret"

    monkeypatch.setattr(
        "swe.config.utils.get_tenant_env",
        fake_get_tenant_env,
    )

    result = await execute_handler(
        HttpHookHandlerConfig(
            id="http-secret",
            url="https://hooks.example/secret",
            headerSecretRefs={"Authorization": "HOOK_TOKEN"},
        ),
        _context(),
        workspace_dir=Path("/tmp/tenant-a/workspaces/default"),
    )

    assert result.failed is False
    assert observed["Authorization"] == "tenant-secret"
    assert tenant_calls == [("HOOK_TOKEN", "tenant-a")]


def test_merge_priority_additional_context_and_updated_input_conflict() -> (
    None
):
    first = CommandHookHandlerConfig(id="first", command="echo")
    second = CommandHookHandlerConfig(id="second", command="echo")
    third = CommandHookHandlerConfig(id="third", command="echo")
    plan = _plan(first, second, third)
    results = [
        plan.handlers[2].success(
            {
                "hookSpecificOutput": {
                    "additionalContext": "third",
                    "permissionDecision": "allow",
                },
            },
        ),
        plan.handlers[0].success(
            {
                "hookSpecificOutput": {
                    "additionalContext": "first",
                    "updatedInput": {"cmd": "echo one"},
                },
            },
        ),
        plan.handlers[1].success(
            {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "no",
                    "updatedInput": {"cmd": "echo two"},
                },
            },
        ),
    ]

    merged = merge_hook_results(plan, results)

    assert merged.decision == HookDecision.BLOCK
    assert "updatedInput" in merged.reason
    assert merged.updated_input is None
    assert [item.context for item in merged.additional_context] == [
        "first",
        "third",
    ]
    assert list(merged.hook_specific_outputs) == ["first", "second", "third"]
    assert [
        (item.handler_id, item.decision, item.reason)
        for item in merged.permission_decisions
    ] == [
        ("second", HookDecision.DENY, "no"),
        ("third", HookDecision.ALLOW, ""),
    ]


def test_merge_continue_false_overrides_other_decisions() -> None:
    stopper = CommandHookHandlerConfig(id="stopper", command="echo")
    asker = CommandHookHandlerConfig(id="asker", command="echo")
    plan = _plan(stopper, asker)
    merged = merge_hook_results(
        plan,
        [
            plan.handlers[1].success(
                {
                    "hookSpecificOutput": {
                        "permissionDecision": "ask",
                        "permissionDecisionReason": "review",
                    },
                },
            ),
            plan.handlers[0].success(
                {"continue": False, "stopReason": "stop now"},
            ),
        ],
    )

    assert merged.decision == HookDecision.STOP
    assert merged.reason == "stop now"
