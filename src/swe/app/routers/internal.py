# -*- coding: utf-8 -*-
"""Internal API for service-to-service communication."""

import base64
import json
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException, Request

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)

# 内部服务认证 Token（可选）
_INTERNAL_TOKEN = os.environ.get("SWE_INTERNAL_TOKEN", "")


def _verify_internal_token(token: Optional[str]) -> None:
    """验证内部服务 Token（如果配置了的话）."""
    if _INTERNAL_TOKEN:
        if not token or token != f"Bearer {_INTERNAL_TOKEN}":
            raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/agents/{agent_id}/reload")
async def internal_reload_agent(
    agent_id: str,
    request: Request,
    tenant_id: str = "default",
    x_internal_token: Optional[str] = Header(
        default=None,
        alias="X-Internal-Token",
    ),
):
    """内部服务调用：重载指定 Agent.

    用于 market 服务修改技能配置后通知主服务重载 Agent。
    """
    _verify_internal_token(x_internal_token)

    manager = getattr(request.app.state, "multi_agent_manager", None)
    if manager is None:
        logger.warning("MultiAgentManager not initialized")
        raise HTTPException(status_code=503, detail="Manager not available")

    try:
        await manager.reload_agent(agent_id, tenant_id=tenant_id)
        logger.info(
            f"Agent '{agent_id}' (tenant={tenant_id}) reloaded via internal API",
        )
        return {"success": True, "agent_id": agent_id, "tenant_id": tenant_id}
    except Exception as e:
        logger.error(f"Failed to reload agent '{agent_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _get_cron_manager(manager, tenant_id: str, agent_id: str):
    """获取指定 tenant/agent 的 CronManager 实例。"""
    ws = manager.get_workspace(tenant_id, agent_id)
    if ws is None:
        return None
    return ws.cron_manager


# ── Cron trigger endpoints ──


@router.post("/cron/tenants/{tenant_id}/agents/{agent_id}/jobs/{job_id}/run")
async def internal_cron_run_job(
    tenant_id: str,
    agent_id: str,
    job_id: str,
    request: Request,
    x_internal_token: Optional[str] = Header(
        default=None,
        alias="X-Internal-Token",
    ),
):
    """内部服务调用：运行指定 cron 任务。"""
    _verify_internal_token(x_internal_token)

    manager = getattr(request.app.state, "multi_agent_manager", None)
    if manager is None:
        logger.warning("MultiAgentManager not initialized")
        raise HTTPException(status_code=503, detail="Manager not available")

    try:
        mgr = _get_cron_manager(manager, tenant_id, agent_id)
        if mgr is None:
            raise HTTPException(
                status_code=404,
                detail="CronManager not found",
            )

        # 检查任务是否存在
        job = await mgr._repo.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' not found",
            )

        # 检查任务是否启用
        if not job.enabled:
            raise HTTPException(
                status_code=409,
                detail=f"Job '{job_id}' is disabled",
            )

        await mgr.run_job(job_id)
        logger.info(
            f"Job '{job_id}' (tenant={tenant_id}, agent={agent_id}) "
            f"triggered via internal API",
        )
        return {"status": "ok", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run job '{job_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cron/tenants/{tenant_id}/agents/{agent_id}/heartbeat/run")
async def internal_cron_run_heartbeat(
    tenant_id: str,
    agent_id: str,
    request: Request,
    x_internal_token: Optional[str] = Header(
        default=None,
        alias="X-Internal-Token",
    ),
):
    """内部服务调用：运行 cron 心跳。"""
    _verify_internal_token(x_internal_token)

    manager = getattr(request.app.state, "multi_agent_manager", None)
    if manager is None:
        logger.warning("MultiAgentManager not initialized")
        raise HTTPException(status_code=503, detail="Manager not available")

    try:
        mgr = _get_cron_manager(manager, tenant_id, agent_id)
        if mgr is None:
            raise HTTPException(
                status_code=404,
                detail="CronManager not found",
            )

        await mgr.run_heartbeat()
        logger.info(
            f"Heartbeat (tenant={tenant_id}, agent={agent_id}) "
            f"triggered via internal API",
        )
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cron/tenants/{tenant_id}/agents/{agent_id}/dream/run")
async def internal_cron_run_dream(
    tenant_id: str,
    agent_id: str,
    request: Request,
    x_internal_token: Optional[str] = Header(
        default=None,
        alias="X-Internal-Token",
    ),
):
    """内部服务调用：运行 cron dream。"""
    _verify_internal_token(x_internal_token)

    manager = getattr(request.app.state, "multi_agent_manager", None)
    if manager is None:
        logger.warning("MultiAgentManager not initialized")
        raise HTTPException(status_code=503, detail="Manager not available")

    try:
        mgr = _get_cron_manager(manager, tenant_id, agent_id)
        if mgr is None:
            raise HTTPException(
                status_code=404,
                detail="CronManager not found",
            )

        await mgr.run_dream()
        logger.info(
            f"Dream (tenant={tenant_id}, agent={agent_id}) "
            f"triggered via internal API",
        )
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run dream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Unified callback endpoint (jobParam-based) ──


@router.post("/cron/callback")
async def internal_cron_callback(
    request: Request,
    x_internal_token: Optional[str] = Header(
        default=None,
        alias="X-Internal-Token",
    ),
    body: Dict[str, Any] = Body(...),
):
    """外部调度平台统一回调端点。

    从 jobParam（base64 JSON）中解码 tenant_id、agent_id、
    task_type 和 job_id，分发到对应的 CronManager 方法。
    """
    _verify_internal_token(x_internal_token)

    job_param = body.get("jobParam") or body.get("job_param") or ""
    if not job_param:
        raise HTTPException(status_code=400, detail="Missing jobParam")

    try:
        params = json.loads(base64.urlsafe_b64decode(job_param))
        tenant_id = params["tenant_id"]
        agent_id = params["agent_id"]
        task_type = params["task_type"]
        job_id = params.get("job_id", "")
    except Exception as e:
        logger.warning("Failed to decode jobParam: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid jobParam: {e}")

    manager = getattr(request.app.state, "multi_agent_manager", None)
    if manager is None:
        logger.warning("MultiAgentManager not initialized")
        raise HTTPException(status_code=503, detail="Manager not available")

    mgr = await _get_cron_manager(manager, tenant_id, agent_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail="CronManager not found")

    try:
        if task_type == "heartbeat":
            await mgr.run_heartbeat()
        elif task_type == "dream":
            await mgr.run_dream()
        else:
            if not job_id:
                raise HTTPException(
                    status_code=400,
                    detail="job_id required for task_type=job",
                )
            await mgr.run_job(job_id)

        logger.info(
            "Callback dispatched: type=%s tenant=%s agent=%s job=%s",
            task_type,
            tenant_id,
            agent_id,
            job_id,
        )
        return {"status": "ok", "task_type": task_type}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to run callback (type=%s, tenant=%s, agent=%s, job=%s): %s",
            task_type,
            tenant_id,
            agent_id,
            job_id,
            e,
        )
        raise HTTPException(status_code=500, detail=str(e))
