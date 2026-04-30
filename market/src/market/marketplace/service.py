# -*- coding: utf-8 -*-
"""应用市场业务服务."""
from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..database.connection import DatabaseConnection
from .fs import (
    _mask_env_value,
    copy_mcp_to_user,
    copy_skill_to_user,
    get_mcp_dir,
    get_skill_dir,
    get_user_skills_dir,
    load_index,
    load_mcp_config,
    save_index,
    save_mcp_config,
)
from .models import MarketItem
from .schemas import (
    DistributeRequest,
    DistributeResponse,
    MarketMCPDetail,
    MarketMCPItem,
    MarketSkillDetail,
    MarketSkillResponse,
    MCPConfigDetail,
    MCPUserStat,
    MySkillItem,
    PublishMCPRequest,
    PublishSkillRequest,
    SkillUserStat,
)

logger = logging.getLogger(__name__)

_TRACING_STATS_SQL = """
    SELECT
        COUNT(*) AS call_count,
        COUNT(DISTINCT user_id) AS user_count
    FROM swe_tracing_spans
    WHERE event_type = 'skill_invocation'
      AND skill_name = %s
      AND source_id = %s
"""

_TRACING_USER_STATS_SQL = """
    SELECT
        user_id,
        MAX(COALESCE(metadata->>'$.user_name', '')) AS user_name,
        COUNT(*) AS call_count
    FROM swe_tracing_spans
    WHERE event_type = 'skill_invocation'
      AND skill_name = %s
      AND source_id = %s
    GROUP BY user_id
    ORDER BY call_count DESC
    LIMIT 100
"""

# MCP 专用统计 SQL - 使用 mcp_server 字段匹配 client_key
_TRACING_STATS_MCP_SQL = """
    SELECT
        COUNT(*) AS call_count,
        COUNT(DISTINCT user_id) AS user_count
    FROM swe_tracing_spans
    WHERE mcp_server = %s
      AND source_id = %s
"""

_TRACING_USER_STATS_MCP_SQL = """
    SELECT
        user_id,
        MAX(COALESCE(metadata->>'$.user_name', '')) AS user_name,
        COUNT(*) AS call_count
    FROM swe_tracing_spans
    WHERE mcp_server = %s
      AND source_id = %s
    GROUP BY user_id
    ORDER BY call_count DESC
    LIMIT 100
"""

_LOG_MARKET_OP_SQL = """
    INSERT INTO swe_marketplace_operation_logs
        (source_id, operator_id, operator_name, operation,
         item_type, item_id, item_name,
         target_user_id, target_user_name, target_bbk_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_QUERY_USERS_BY_SOURCE_SQL = """
    SELECT tenant_id, tenant_name, bbk_id
    FROM swe_tenant_init_source
    WHERE source_id = %s
"""

_QUERY_USERS_BY_BBK_SQL = """
    SELECT tenant_id, tenant_name, bbk_id
    FROM swe_tenant_init_source
    WHERE source_id = %s AND bbk_id IN ({placeholders})
"""


def _bump_patch(version: str) -> str:
    """Increment patch version: '1.0.0' -> '1.0.1'."""
    parts = version.split(".")
    if len(parts) == 3:
        try:
            parts[2] = str(int(parts[2]) + 1)
            return ".".join(parts)
        except ValueError:
            pass
    return version + ".1"


def _item_visible(item: MarketItem, user_bbk_id: str) -> bool:
    """Return True if item is visible to user with given bbk_id."""
    if item.status != "active":
        return False
    if user_bbk_id == "100":
        return True
    if not item.bbk_ids:
        return True
    return "100" in item.bbk_ids or user_bbk_id in item.bbk_ids


class MarketplaceService:
    def __init__(
        self,
        db: DatabaseConnection,
        marketplace_root: Path,
        swe_root: Path,
    ) -> None:
        self.db = db
        self.marketplace_root = marketplace_root
        self.swe_root = swe_root

    async def publish_skill(
        self,
        source_id: str,
        req: PublishSkillRequest,
    ) -> MarketItem:
        """上架技能。同名技能已存在时递增 patch 版本号。"""
        items = load_index(self.marketplace_root, source_id)
        existing = next((i for i in items if i.name == req.name), None)

        now = datetime.now(timezone.utc).isoformat()
        if existing is not None:
            version = _bump_patch(existing.version)
            existing.version = version
            existing.description = req.description
            existing.creator_id = req.creator_id
            existing.creator_name = req.creator_name
            existing.category_id = req.category_id
            existing.bbk_ids = req.bbk_ids
            existing.status = "active"
            existing.updated_at = now
            item = existing
        else:
            item = MarketItem(
                item_id=str(uuid.uuid4()),
                item_type="skill",
                name=req.name,
                description=req.description,
                version="1.0.0",
                creator_id=req.creator_id,
                creator_name=req.creator_name,
                category_id=req.category_id,
                bbk_ids=req.bbk_ids,
                status="active",
                created_at=now,
                updated_at=now,
            )
            items.append(item)

        skill_dir = get_skill_dir(
            self.marketplace_root,
            source_id,
            item.item_id,
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "skill.json").write_text(
            json.dumps(req.skill_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if req.skill_md:
            (skill_dir / "SKILL.md").write_text(req.skill_md, encoding="utf-8")

        save_index(self.marketplace_root, source_id, items)

        if self.db.is_connected:
            try:
                await self.db.execute(
                    _LOG_MARKET_OP_SQL,
                    (
                        source_id,
                        req.creator_id,
                        req.creator_name,
                        "publish",
                        "skill",
                        item.item_id,
                        item.name,
                        None,
                        None,
                        None,
                    ),
                )
            except Exception as e:
                logger.warning("Failed to log publish operation: %s", e)

        return item

    async def unpublish_skill(
        self,
        source_id: str,
        item_id: str,
        operator_id: str,
        operator_name: str,
    ) -> bool:
        """下架技能（设为 inactive）。返回 True 表示成功。"""
        items = load_index(self.marketplace_root, source_id)
        item = next((i for i in items if i.item_id == item_id), None)
        if item is None:
            return False
        item.status = "inactive"
        item.updated_at = datetime.now(timezone.utc).isoformat()
        save_index(self.marketplace_root, source_id, items)

        if self.db.is_connected:
            try:
                await self.db.execute(
                    _LOG_MARKET_OP_SQL,
                    (
                        source_id,
                        operator_id,
                        operator_name,
                        "unpublish",
                        "skill",
                        item_id,
                        item.name,
                        None,
                        None,
                        None,
                    ),
                )
            except Exception as e:
                logger.warning("Failed to log unpublish operation: %s", e)

        return True

    async def list_skills(
        self,
        source_id: str,
        user_bbk_id: str,
        category_id: Optional[int] = None,
    ) -> list[MarketSkillResponse]:
        """列出市场技能，按 bbk_id 过滤，可选按分类过滤。"""
        items = load_index(self.marketplace_root, source_id)
        visible = [i for i in items if _item_visible(i, user_bbk_id)]
        if category_id is not None:
            visible = [i for i in visible if i.category_id == category_id]

        result = []
        for item in visible:
            call_count, user_count = await self._get_stats(
                item.name,
                source_id,
            )
            result.append(
                MarketSkillResponse(
                    item_id=item.item_id,
                    name=item.name,
                    description=item.description,
                    version=item.version,
                    creator_id=item.creator_id,
                    creator_name=item.creator_name,
                    category_id=item.category_id,
                    bbk_ids=item.bbk_ids,
                    status=item.status,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    call_count=call_count,
                    user_count=user_count,
                ),
            )
        return result

    async def get_skill_detail(
        self,
        source_id: str,
        item_id: str,
        user_bbk_id: str,
    ) -> Optional[MarketSkillDetail]:
        """获取技能详情（含调用客户明细）。"""
        items = load_index(self.marketplace_root, source_id)
        item = next((i for i in items if i.item_id == item_id), None)
        if item is None or not _item_visible(item, user_bbk_id):
            return None

        call_count, user_count = await self._get_stats(item.name, source_id)
        user_stats = await self._get_user_stats(item.name, source_id)

        return MarketSkillDetail(
            item_id=item.item_id,
            name=item.name,
            description=item.description,
            version=item.version,
            creator_id=item.creator_id,
            creator_name=item.creator_name,
            category_id=item.category_id,
            bbk_ids=item.bbk_ids,
            status=item.status,
            created_at=item.created_at,
            updated_at=item.updated_at,
            call_count=call_count,
            user_count=user_count,
            user_stats=user_stats,
        )

    async def distribute_skill(
        self,
        source_id: str,
        item_id: str,
        operator_id: str,
        operator_name: str,
        req: DistributeRequest,
    ) -> DistributeResponse:
        """分发技能到目标用户工作目录，并写操作日志。"""
        items = load_index(self.marketplace_root, source_id)
        item = next((i for i in items if i.item_id == item_id), None)
        if item is None:
            raise ValueError(f"Item {item_id} not found in source {source_id}")

        target_users = await self._resolve_target_users(source_id, req)
        count = 0
        for user in target_users:
            try:
                copy_skill_to_user(
                    marketplace_root=self.marketplace_root,
                    source_id=source_id,
                    item_id=item_id,
                    swe_root=self.swe_root,
                    user_id=user["tenant_id"],
                    skill_name=item.name,
                    distributed_by=operator_id,
                    version=item.version,
                )
                count += 1
            except Exception as e:
                logger.warning(
                    "Failed to copy skill to user %s: %s",
                    user["tenant_id"],
                    e,
                )
                continue

            if self.db.is_connected:
                try:
                    await self.db.execute(
                        _LOG_MARKET_OP_SQL,
                        (
                            source_id,
                            operator_id,
                            operator_name,
                            "distribute",
                            "skill",
                            item_id,
                            item.name,
                            user["tenant_id"],
                            user.get("tenant_name", ""),
                            user.get("bbk_id", ""),
                        ),
                    )
                except Exception as e:
                    logger.warning("Failed to log distribute operation: %s", e)

        return DistributeResponse(distributed_count=count, item_id=item_id)

    async def get_my_skills(
        self,
        source_id: str,
        user_id: str,
        agent_id: str = "default",
    ) -> list[MySkillItem]:
        """获取用户技能列表（我创建的 + 我接收的）。"""
        skills_dir = get_user_skills_dir(self.swe_root, user_id, agent_id)
        if not skills_dir.exists():
            return []

        market_index = load_index(self.marketplace_root, source_id)
        market_versions: dict[str, str] = {
            i.name: i.version for i in market_index if i.status == "active"
        }

        result = []
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_json_path = skill_dir / "skill.json"
            if not skill_json_path.exists():
                continue
            try:
                data = json.loads(skill_json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            source = data.get("source", "customized")
            is_received = source.startswith("marketplace:")
            received_version = data.get("received_version")
            market_version = market_versions.get(skill_dir.name)
            has_update = (
                is_received
                and received_version is not None
                and market_version is not None
                and received_version != market_version
            )

            result.append(
                MySkillItem(
                    skill_name=skill_dir.name,
                    source=source,
                    description=data.get("description", ""),
                    version=data.get("version"),
                    received_version=received_version,
                    distributed_by=data.get("distributed_by"),
                    is_received=is_received,
                    has_update=has_update,
                ),
            )
        return result

    async def _get_stats(
        self,
        skill_name: str,
        source_id: str,
    ) -> tuple[int, int]:
        if not self.db.is_connected:
            return 0, 0
        try:
            row = await self.db.fetch_one(
                _TRACING_STATS_SQL,
                (skill_name, source_id),
            )
            if row:
                return int(row.get("call_count", 0)), int(
                    row.get("user_count", 0),
                )
        except Exception as e:
            logger.warning("Failed to fetch stats for %s: %s", skill_name, e)
        return 0, 0

    async def _get_user_stats(
        self,
        skill_name: str,
        source_id: str,
    ) -> list[SkillUserStat]:
        if not self.db.is_connected:
            return []
        try:
            rows = await self.db.fetch_all(
                _TRACING_USER_STATS_SQL,
                (skill_name, source_id),
            )
            return [
                SkillUserStat(
                    user_id=r["user_id"],
                    user_name=r.get("user_name", ""),
                    call_count=int(r["call_count"]),
                )
                for r in rows
            ]
        except Exception as e:
            logger.warning(
                "Failed to fetch user stats for %s: %s",
                skill_name,
                e,
            )
        return []

    async def _resolve_target_users(
        self,
        source_id: str,
        req: DistributeRequest,
    ) -> list[dict]:
        if not self.db.is_connected:
            return []
        try:
            if req.target_type == "all":
                return await self.db.fetch_all(
                    _QUERY_USERS_BY_SOURCE_SQL,
                    (source_id,),
                )
            if req.target_type == "bbk_id" and req.target_values:
                placeholders = ",".join(["%s"] * len(req.target_values))
                sql = _QUERY_USERS_BY_BBK_SQL.format(placeholders=placeholders)
                return await self.db.fetch_all(
                    sql,
                    (source_id, *req.target_values),
                )
            if req.target_type == "user_id" and req.target_values:
                return [
                    {"tenant_id": uid, "tenant_name": "", "bbk_id": ""}
                    for uid in req.target_values
                ]
        except Exception as e:
            logger.warning("Failed to resolve target users: %s", e)
        return []

    # ============ MCP 服务方法 ============

    async def publish_mcp(
        self,
        source_id: str,
        req: PublishMCPRequest,
    ) -> MarketItem:
        """发布 MCP 到市场。覆盖已存在条目。

        Args:
            source_id: 来源 ID。
            req: 发布请求体。

        Returns:
            创建或更新的 MarketItem。
        """
        items = load_index(self.marketplace_root, source_id)

        # 按 client_key 查找已存在的 MCP 条目
        existing = next(
            (i for i in items if i.item_type == "mcp" and i.client_key == req.client_key),
            None,
        )

        now = datetime.now(timezone.utc).isoformat()
        if existing is not None:
            # 覆盖：复用 item_id
            existing.name = req.name
            existing.description = req.description
            existing.creator_id = req.creator_id
            existing.creator_name = req.creator_name
            existing.category_id = req.category_id
            existing.bbk_ids = req.bbk_ids
            existing.status = "active"
            existing.updated_at = now
            item = existing
        else:
            # 创建新条目
            item = MarketItem(
                item_id=str(uuid.uuid4()),
                item_type="mcp",
                client_key=req.client_key,
                name=req.name,
                description=req.description,
                creator_id=req.creator_id,
                creator_name=req.creator_name,
                category_id=req.category_id,
                bbk_ids=req.bbk_ids,
                status="active",
                created_at=now,
                updated_at=now,
            )
            items.append(item)

        # 保存 MCP 配置文件
        mcp_config = {
            "client_key": req.client_key,
            "config": req.config,
        }
        save_mcp_config(self.marketplace_root, source_id, item.item_id, mcp_config)

        # 更新索引
        save_index(self.marketplace_root, source_id, items)

        # 记录操作日志
        if self.db.is_connected:
            try:
                await self.db.execute(
                    _LOG_MARKET_OP_SQL,
                    (
                        source_id,
                        req.creator_id,
                        req.creator_name,
                        "publish",
                        "mcp",
                        item.item_id,
                        item.name,
                        None,
                        None,
                        None,
                    ),
                )
            except Exception as e:
                logger.warning("Failed to log MCP publish operation: %s", e)

        return item

    async def list_mcp_items(
        self,
        source_id: str,
        user_bbk_id: str,
        category_id: Optional[int] = None,
    ) -> list[MarketMCPItem]:
        """列出市场 MCP 条目。

        Args:
            source_id: 来源 ID。
            user_bbk_id: 用户 bbk_id，用于权限过滤。
            category_id: 可选的分类 ID 过滤。

        Returns:
            MCP 条目列表（含调用统计）。
        """
        items = load_index(self.marketplace_root, source_id)
        mcp_items = [i for i in items if i.item_type == "mcp" and _item_visible(i, user_bbk_id)]

        if category_id is not None:
            mcp_items = [i for i in mcp_items if i.category_id == category_id]

        result = []
        for item in mcp_items:
            call_count, user_count = await self._get_mcp_stats(
                item.client_key,
                source_id,
            )
            result.append(
                MarketMCPItem(
                    item_id=item.item_id,
                    client_key=item.client_key,
                    name=item.name,
                    description=item.description,
                    creator_id=item.creator_id,
                    creator_name=item.creator_name,
                    category_id=item.category_id,
                    bbk_ids=item.bbk_ids,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    call_count=call_count,
                    user_count=user_count,
                ),
            )
        return result

    async def get_mcp_detail(
        self,
        source_id: str,
        item_id: str,
        user_bbk_id: str,
    ) -> Optional[MarketMCPDetail]:
        """获取 MCP 详情（含配置和用户统计）。

        Args:
            source_id: 来源 ID。
            item_id: 条目 ID。
            user_bbk_id: 用户 bbk_id，用于权限过滤。

        Returns:
            MCP 详情，不存在或无权限返回 None。
        """
        items = load_index(self.marketplace_root, source_id)
        item = next(
            (i for i in items if i.item_id == item_id and i.item_type == "mcp"),
            None,
        )
        if item is None or not _item_visible(item, user_bbk_id):
            return None

        # 加载 MCP 配置
        mcp_config = load_mcp_config(self.marketplace_root, source_id, item_id)
        if mcp_config is None:
            return None

        call_count, user_count = await self._get_mcp_stats(item.client_key, source_id)
        user_stats = await self._get_mcp_user_stats(item.client_key, source_id)

        # 获取并脱敏敏感字段
        config_data = mcp_config.get("config", {})
        masked_env = {k: _mask_env_value(v) for k, v in config_data.get("env", {}).items()}
        masked_headers = {k: _mask_env_value(v) for k, v in config_data.get("headers", {}).items()}

        return MarketMCPDetail(
            item_id=item.item_id,
            client_key=item.client_key,
            name=item.name,
            description=item.description,
            creator_id=item.creator_id,
            creator_name=item.creator_name,
            category_id=item.category_id,
            bbk_ids=item.bbk_ids,
            created_at=item.created_at,
            updated_at=item.updated_at,
            call_count=call_count,
            user_count=user_count,
            config=MCPConfigDetail(
                transport=config_data.get("transport", "stdio"),
                url=config_data.get("url", ""),
                headers=masked_headers,
                command=config_data.get("command", ""),
                args=config_data.get("args", []),
                env=masked_env,
                cwd=config_data.get("cwd", ""),
                lazy_load=config_data.get("lazy_load", False),
            ),
            user_stats=user_stats,
        )

    async def distribute_mcp(
        self,
        source_id: str,
        item_id: str,
        operator_id: str,
        operator_name: str,
        req: DistributeRequest,
    ) -> DistributeResponse:
        """分发 MCP 到目标用户。

        Args:
            source_id: 来源 ID。
            item_id: 条目 ID。
            operator_id: 操作者 ID。
            operator_name: 操作者名称。
            req: 分发请求体。

        Returns:
            分发结果（成功数量和条目 ID）。

        Raises:
            ValueError: 条目不存在。
        """
        items = load_index(self.marketplace_root, source_id)
        item = next(
            (i for i in items if i.item_id == item_id and i.item_type == "mcp"),
            None,
        )
        if item is None:
            raise ValueError(f"MCP item {item_id} not found in source {source_id}")

        target_users = await self._resolve_target_users(source_id, req)
        count = 0

        for user in target_users:
            try:
                copy_mcp_to_user(
                    marketplace_root=self.marketplace_root,
                    source_id=source_id,
                    item_id=item_id,
                    swe_root=self.swe_root,
                    user_id=user["tenant_id"],
                    client_key=item.client_key,
                    distributed_by=operator_id,
                )
                count += 1

                # 记录分发日志
                if self.db.is_connected:
                    try:
                        await self.db.execute(
                            _LOG_MARKET_OP_SQL,
                            (
                                source_id,
                                operator_id,
                                operator_name,
                                "distribute",
                                "mcp",
                                item_id,
                                item.name,
                                user["tenant_id"],
                                user.get("tenant_name", ""),
                                user.get("bbk_id", ""),
                            ),
                        )
                    except Exception as e:
                        logger.warning("Failed to log MCP distribute operation: %s", e)
            except Exception as e:
                logger.warning(
                    "Failed to copy MCP to user %s: %s",
                    user["tenant_id"],
                    e,
                )
                continue

        return DistributeResponse(distributed_count=count, item_id=item_id)

    async def delete_mcp(
        self,
        source_id: str,
        item_id: str,
        operator_id: str = "",
        operator_name: str = "",
    ) -> bool:
        """删除市场 MCP 条目。

        Args:
            source_id: 来源 ID。
            item_id: 条目 ID。
            operator_id: 操作者 ID（可选）。
            operator_name: 操作者名称（可选）。

        Returns:
            True 表示删除成功，False 表示条目不存在。
        """
        items = load_index(self.marketplace_root, source_id)
        item = next(
            (i for i in items if i.item_id == item_id and i.item_type == "mcp"),
            None,
        )
        if item is None:
            return False

        # 从索引中移除
        items.remove(item)
        save_index(self.marketplace_root, source_id, items)

        # 删除配置目录
        mcp_dir = get_mcp_dir(self.marketplace_root, source_id, item_id)
        if mcp_dir.exists():
            shutil.rmtree(mcp_dir)

        # 记录删除日志
        if self.db.is_connected:
            try:
                await self.db.execute(
                    _LOG_MARKET_OP_SQL,
                    (
                        source_id,
                        operator_id,
                        operator_name,
                        "delete",
                        "mcp",
                        item_id,
                        item.name,
                        None,
                        None,
                        None,
                    ),
                )
            except Exception as e:
                logger.warning("Failed to log MCP delete operation: %s", e)

        return True

    async def _get_mcp_stats(
        self,
        client_key: str,
        source_id: str,
    ) -> tuple[int, int]:
        """获取 MCP 调用统计。

        Args:
            client_key: MCP 客户端标识。
            source_id: 来源 ID。

        Returns:
            (调用次数, 用户数)。
        """
        if not self.db.is_connected:
            return 0, 0
        try:
            row = await self.db.fetch_one(
                _TRACING_STATS_MCP_SQL,
                (client_key, source_id),
            )
            if row:
                return int(row.get("call_count", 0)), int(row.get("user_count", 0))
        except Exception as e:
            logger.warning("Failed to get MCP stats for %s: %s", client_key, e)
        return 0, 0

    async def _get_mcp_user_stats(
        self,
        client_key: str,
        source_id: str,
    ) -> list[MCPUserStat]:
        """获取 MCP 用户统计明细。

        Args:
            client_key: MCP 客户端标识。
            source_id: 来源 ID。

        Returns:
            用户统计列表（最多 100 条）。
        """
        if not self.db.is_connected:
            return []
        try:
            rows = await self.db.fetch_all(
                _TRACING_USER_STATS_MCP_SQL,
                (client_key, source_id),
            )
            return [
                MCPUserStat(
                    user_id=r["user_id"],
                    user_name=r.get("user_name", ""),
                    call_count=int(r["call_count"]),
                )
                for r in rows
            ]
        except Exception as e:
            logger.warning("Failed to get MCP user stats for %s: %s", client_key, e)
        return []
