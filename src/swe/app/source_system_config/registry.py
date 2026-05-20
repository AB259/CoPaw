# -*- coding: utf-8 -*-
"""Source 系统配置注册表与默认值裁剪规则。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceSystemConfigSwitch:
    """描述一个受代码注册管理的 source 系统开关。"""

    key: str
    path: tuple[str, ...]
    default_value: Any


CHAT_TASK_PROGRESS_ENABLED_SWITCH = SourceSystemConfigSwitch(
    key="feature_switches.chat_task_progress_enabled",
    path=("feature_switches", "chat_task_progress_enabled"),
    default_value=True,
)

CURRENT_SOURCE_SYSTEM_CONFIG_SWITCHES: tuple[SourceSystemConfigSwitch, ...] = (
    CHAT_TASK_PROGRESS_ENABLED_SWITCH,
)

_MISSING = object()


def build_default_source_system_config_payload() -> dict[str, Any]:
    """根据注册表生成默认 source 系统配置。"""
    payload: dict[str, Any] = {}
    for switch in CURRENT_SOURCE_SYSTEM_CONFIG_SWITCHES:
        payload = _deep_merge_dicts(
            payload,
            _build_nested_payload(switch.path, switch.default_value),
        )
    return payload


def merge_source_system_config_with_defaults(
    raw_config: dict[str, Any],
) -> dict[str, Any]:
    """将原始配置与注册默认值做深度合并。"""
    return _deep_merge_dicts(
        build_default_source_system_config_payload(),
        raw_config,
    )


def prune_registered_default_overrides(
    raw_config: dict[str, Any],
) -> dict[str, Any]:
    """删除与注册默认值相同的显式覆盖，并清理空父节点。"""
    pruned = deepcopy(raw_config)
    for switch in CURRENT_SOURCE_SYSTEM_CONFIG_SWITCHES:
        value = _get_nested_value(pruned, switch.path)
        if value is _MISSING:
            continue
        if value == switch.default_value:
            _delete_nested_path(pruned, switch.path)
    return pruned


def is_chat_task_progress_enabled(config: Any | None) -> bool:
    """读取 task progress 开关，缺失时回退为默认启用。"""
    raw_config = _normalize_config_payload(config)
    merged = merge_source_system_config_with_defaults(raw_config)
    value = _get_nested_value(
        merged,
        CHAT_TASK_PROGRESS_ENABLED_SWITCH.path,
    )
    if value is _MISSING:
        return bool(CHAT_TASK_PROGRESS_ENABLED_SWITCH.default_value)
    return bool(value)


def _normalize_config_payload(config: Any | None) -> dict[str, Any]:
    """兼容模型对象与普通 dict，统一提取配置对象。"""
    if config is None:
        return {}
    if hasattr(config, "config"):
        return _normalize_config_payload(getattr(config, "config"))
    if hasattr(config, "as_dict"):
        return config.as_dict()
    if isinstance(config, dict):
        return deepcopy(config)
    return {}


def _build_nested_payload(
    path: tuple[str, ...],
    value: Any,
) -> dict[str, Any]:
    """将点状路径构造成嵌套字典。"""
    nested: Any = deepcopy(value)
    for key in reversed(path):
        nested = {key: nested}
    return nested


def _deep_merge_dicts(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    """递归合并配置，保留未知键并允许局部覆盖。"""
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(current, value)
            continue
        merged[key] = deepcopy(value)
    return merged


def _get_nested_value(
    payload: dict[str, Any],
    path: tuple[str, ...],
) -> Any:
    """读取嵌套路径的值，缺失时返回哨兵对象。"""
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return _MISSING
        current = current[key]
    return current


def _delete_nested_path(
    payload: dict[str, Any],
    path: tuple[str, ...],
) -> None:
    """删除嵌套路径，并向上裁剪变为空对象的父节点。"""
    parents: list[tuple[dict[str, Any], str]] = []
    current: Any = payload
    for key in path[:-1]:
        if not isinstance(current, dict):
            return
        next_current = current.get(key)
        if not isinstance(next_current, dict):
            return
        parents.append((current, key))
        current = next_current
    if not isinstance(current, dict):
        return
    current.pop(path[-1], None)
    while parents:
        parent, key = parents.pop()
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key, None)


__all__ = [
    "CHAT_TASK_PROGRESS_ENABLED_SWITCH",
    "CURRENT_SOURCE_SYSTEM_CONFIG_SWITCHES",
    "SourceSystemConfigSwitch",
    "build_default_source_system_config_payload",
    "is_chat_task_progress_enabled",
    "merge_source_system_config_with_defaults",
    "prune_registered_default_overrides",
]
