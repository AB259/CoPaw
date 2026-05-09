# -*- coding: utf-8 -*-
"""定时任务调度平台适配器。

定义外部调度平台的抽象接口，以及一个空操作的本地实现（Noop）。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SchedulerAdapter(ABC):
    """外部调度平台适配器抽象基类。"""

    @abstractmethod
    async def register_job(
        self,
        tenant_id: str,
        agent_id: str,
        task_type: str,
        job_id: str,
        cron: str,
        callback_url: str,
    ) -> str:
        """向外部调度平台注册一个定时任务。

        Args:
            tenant_id: 租户 ID
            agent_id: Agent ID
            task_type: 任务类型（"job" | "heartbeat" | "dream"）
            job_id: Copaw 内部 job ID
            cron: cron 表达式
            callback_url: 完整的回调 URL（含 server_domain 前缀）

        Returns:
            外部平台分配的任务 ID（external_job_id）
        """
        raise NotImplementedError

    @abstractmethod
    async def update_job(
        self,
        external_id: str,
        tenant_id: str,
        agent_id: str,
        task_type: str,
        job_id: str,
        cron: str,
        callback_url: str,
    ) -> None:
        """更新外部平台上已注册的任务。

        Args:
            external_id: 外部平台分配的任务 ID
            tenant_id: 租户 ID
            agent_id: Agent ID
            task_type: 任务类型（"job" | "heartbeat" | "dream"）
            job_id: Copaw 内部 job ID
            cron: cron 表达式
            callback_url: 完整的回调 URL（含 server_domain 前缀）
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_job(self, external_id: str) -> None:
        """从外部调度平台删除任务（或停止任务）。

        外部平台不支持真正删除时，退化为 stop。
        """
        raise NotImplementedError

    @abstractmethod
    async def pause_job(self, external_id: str) -> None:
        """暂停外部平台上的任务调度。"""
        raise NotImplementedError

    @abstractmethod
    async def resume_job(self, external_id: str) -> None:
        """恢复外部平台上的任务调度。"""
        raise NotImplementedError


class NoopSchedulerAdapter(SchedulerAdapter):
    """空操作适配器，所有方法仅打日志，不产生外部效果。"""

    async def register_job(
        self,
        tenant_id: str,
        agent_id: str,
        task_type: str,
        job_id: str,
        cron: str,
        callback_url: str,
    ) -> str:
        logger.debug(
            "NoopAdapter.register_job: tenant=%s agent=%s type=%s job=%s cron=%s url=%s",
            tenant_id,
            agent_id,
            task_type,
            job_id,
            cron,
            callback_url,
        )
        return ""

    async def update_job(
        self,
        external_id: str,
        tenant_id: str,
        agent_id: str,
        task_type: str,
        job_id: str,
        cron: str,
        callback_url: str,
    ) -> None:
        logger.debug(
            "NoopAdapter.update_job: ext_id=%s tenant=%s agent=%s type=%s job=%s cron=%s",
            external_id,
            tenant_id,
            agent_id,
            task_type,
            job_id,
            cron,
        )

    async def delete_job(self, external_id: str) -> None:
        logger.debug("NoopAdapter.delete_job: ext_id=%s", external_id)

    async def pause_job(self, external_id: str) -> None:
        logger.debug("NoopAdapter.pause_job: ext_id=%s", external_id)

    async def resume_job(self, external_id: str) -> None:
        logger.debug("NoopAdapter.resume_job: ext_id=%s", external_id)
