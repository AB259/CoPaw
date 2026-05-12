# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest
from pydantic import ValidationError

from swe.agents.hook_runtime.models import HookEventName
from swe.config.config import AgentProfileConfig, Config


def test_root_and_agent_config_parse_hook_matcher_groups() -> None:
    hook_data = {
        "enabled": True,
        "events": {
            "PreToolUse": [
                {
                    "id": "shells",
                    "matcher": {"tools": ["execute_shell_command"]},
                    "hooks": [
                        {
                            "id": "audit",
                            "type": "command",
                            "argv": ["python", "hooks/audit.py"],
                            "if": "tool_name == 'execute_shell_command'",
                            "timeout": 2,
                            "statusMessage": "Checking command",
                            "once": True,
                            "failPolicy": "block",
                        },
                    ],
                },
            ],
        },
    }

    root = Config.model_validate({"hooks": hook_data})
    agent = AgentProfileConfig.model_validate(
        {
            "id": "agent-1",
            "name": "Agent",
            "hooks": hook_data,
        },
    )

    root_handler = root.hooks.events[HookEventName.PRE_TOOL_USE][0].hooks[0]
    agent_handler = agent.hooks.events[HookEventName.PRE_TOOL_USE][0].hooks[0]
    assert root.hooks.enabled is True
    assert root_handler.id == "audit"
    assert root_handler.fail_policy == "block"
    assert agent_handler.once is True


def test_config_rejects_unsupported_mvp_hook_handler_type() -> None:
    with pytest.raises(ValidationError):
        Config.model_validate(
            {
                "hooks": {
                    "enabled": True,
                    "events": {
                        "Stop": [
                            {
                                "hooks": [
                                    {
                                        "id": "unsupported",
                                        "type": "agent",
                                    },
                                ],
                            },
                        ],
                    },
                },
            },
        )
