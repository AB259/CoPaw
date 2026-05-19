# -*- coding: utf-8 -*-
"""Source 系统配置运行时服务与缓存。"""

import logging
import time
from dataclasses import dataclass
from typing import Callable

from .models import (
    DEFAULT_SOURCE_SYSTEM_CONFIG,
    EffectiveSourceSystemConfig,
    SourceSystemConfigRecord,
)
from .store import SourceSystemConfigStore

logger = logging.getLogger(__name__)


class SourceSystemConfigUnavailable(RuntimeError):
    """Source 系统配置存储不可用且没有可用缓存。"""


@dataclass
class _CacheEntry:
    """缓存项包含配置、加载时间和 last-known-good 状态。"""

    effective: EffectiveSourceSystemConfig
    loaded_at: float


class SourceSystemConfigService:
    """解析 source effective config，并提供短 TTL 缓存。"""

    def __init__(
        self,
        store: SourceSystemConfigStore,
        ttl_seconds: int = 30,
        time_fn: Callable[[], float] | None = None,
    ):
        """初始化运行时服务。"""
        self.store = store
        self.ttl_seconds = ttl_seconds
        self._time_fn = time_fn or time.time
        self._cache: dict[str, _CacheEntry] = {}

    async def resolve_config(
        self,
        source_id: str,
        *,
        force_refresh: bool = False,
    ) -> EffectiveSourceSystemConfig:
        """解析 source 的 effective config。"""
        now = self._time_fn()
        cached = self._cache.get(source_id)
        if (
            cached is not None
            and not force_refresh
            and now - cached.loaded_at < self.ttl_seconds
        ):
            return cached.effective

        try:
            record = await self.store.get_config(source_id)
            effective = self._build_effective(source_id, record)
            self._cache[source_id] = _CacheEntry(effective, now)
            return effective
        except Exception as exc:
            if cached is not None:
                logger.warning(
                    "使用 source 系统配置 last-known-good 缓存: source=%s, error=%s",
                    source_id,
                    exc,
                )
                stale = cached.effective.model_copy(
                    update={
                        "stale": True,
                        "last_error": str(exc),
                    },
                )
                self._cache[source_id] = _CacheEntry(stale, now)
                return stale
            raise SourceSystemConfigUnavailable(
                f"source system config unavailable for {source_id}: {exc}",
            ) from exc

    def invalidate(self, source_id: str | None = None) -> None:
        """清理缓存，管理接口更新后当前实例立即生效。"""
        if source_id is None:
            self._cache.clear()
            return
        self._cache.pop(source_id, None)

    def _build_effective(
        self,
        source_id: str,
        record: SourceSystemConfigRecord | None,
    ) -> EffectiveSourceSystemConfig:
        """将默认配置和 source 覆盖合成为运行时配置。"""
        if record is None:
            return EffectiveSourceSystemConfig(
                source_id=source_id,
                config=DEFAULT_SOURCE_SYSTEM_CONFIG,
                version=0,
                is_default=True,
            )

        return EffectiveSourceSystemConfig(
            source_id=source_id,
            config=record.config.merged_with_defaults(),
            version=record.version,
            updated_by=record.updated_by,
            updated_at=record.updated_at,
        )
