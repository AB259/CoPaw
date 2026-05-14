# -*- coding: utf-8 -*-
"""统一导出 Hook 运行时模型与入口。"""

from typing import TYPE_CHECKING

from .models import (
    EffectiveHookPlan,
    FailPolicy,
    HookConfig,
    HookContext,
    HookDecision,
    HookEventName,
    HookSessionOverlay,
    HookSessionState,
    LoadedSkillHookSource,
    PromptHookHandlerConfig,
)

if TYPE_CHECKING:
    from .runtime import HookRuntime

__all__ = [
    "EffectiveHookPlan",
    "FailPolicy",
    "HookConfig",
    "HookContext",
    "HookDecision",
    "HookEventName",
    "HookRuntime",
    "HookSessionOverlay",
    "HookSessionState",
    "LoadedSkillHookSource",
    "PromptHookHandlerConfig",
]


def __getattr__(name: str):
    """按需导入运行时，避免配置模块初始化时触发循环导入。"""
    if name == "HookRuntime":
        from .runtime import HookRuntime as _HookRuntime

        return _HookRuntime
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
