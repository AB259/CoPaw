# -*- coding: utf-8 -*-
"""经营场景查询的本地兜底数据。

外部接口 /api/agent/workspace/skill-config/list 未对接或异常时，
scene-skills 代理接口返回这里的数据（fallback=True），
字段形状与外部接口保持一致。外部接口稳定后本文件可整体删除。
"""

from __future__ import annotations

from .models import CATEGORY_CODE_BY_LABEL, SceneSkillItem

_DEFAULT_CRON_EXAMPLE = "0 9 * * *"

# (中文大类, 场景名, 场景描述, 来源标签, 是否就绪, MCP 列表)
_FALLBACK_ROWS: list[tuple[str, str, str, str, bool, list[str]]] = [
    (
        "保险",
        "保障潜客经营",
        "挖掘高潜保险客户，提升保险客户覆盖",
        "总部预置",
        True,
        ["mcp-customer", "mcp-insurance"],
    ),
    (
        "保险",
        "保障缺口经营",
        "识别客户保障缺口，提供综合保障方案",
        "总部预置",
        True,
        ["mcp-customer", "mcp-insurance"],
    ),
    (
        "理财",
        "产品到期承接",
        "优先承接近期到期资金，提升客户资产留存",
        "总部预置",
        True,
        ["mcp-customer", "mcp-wealth"],
    ),
    (
        "存款",
        "高价值揽客",
        "挖掘客户资金变动机会，提升存款贡献",
        "分行自建",
        True,
        ["mcp-customer", "mcp-deposit"],
    ),
    (
        "代发",
        "代发客户经营",
        "深化代发客户产品覆盖，提升存款贡献",
        "总部预置",
        True,
        ["mcp-customer", "mcp-payroll"],
    ),
    (
        "理财",
        "理财重点客户经营",
        "提升理财配置比例，增强客户黏性",
        "分行自建",
        True,
        ["mcp-customer", "mcp-wealth"],
    ),
    (
        "跨境",
        "跨境客户经营",
        "拓展跨境客户，提升国际业务贡献",
        "总部预置",
        False,
        ["mcp-customer", "mcp-cross-border"],
    ),
    (
        "基金",
        "基金定投提升",
        "推动基金定投业务发展",
        "总部预置",
        True,
        ["mcp-customer", "mcp-fund"],
    ),
]


def fallback_scene_skills(category: str) -> list[SceneSkillItem]:
    """按英文大类 code 返回兜底场景列表。"""
    items: list[SceneSkillItem] = []
    for index, (label, name, desc, source, ready, mcps) in enumerate(
        _FALLBACK_ROWS,
        start=1,
    ):
        code = CATEGORY_CODE_BY_LABEL[label]
        if code != category:
            continue
        items.append(
            SceneSkillItem(
                skillId=f"skill-wealth-{code}-{index}",
                itemId=f"item-wealth-{code}-{index}",
                senceName=name,
                category=code,
                senceDesc=desc,
                cronExample=_DEFAULT_CRON_EXAMPLE,
                mcpRelationList=mcps,
                skillBbkLabel=source,
                ready=ready,
            ),
        )
    return items
