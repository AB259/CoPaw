# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from .models import CronJobSpec

logger = logging.getLogger(__name__)


class CronExecutor:
    def __init__(self, *, runner: Any, channel_manager: Any):
        self._runner = runner
        self._channel_manager = channel_manager

    async def execute(self, job: CronJobSpec) -> None:
        """Execute one job once.

        - task_type text: send fixed text to channel
        - task_type agent: ask agent with prompt, send reply to channel (
            stream_query + send_event)

        For agent tasks:
        - Uses job.created_by for LLM config (the job creator's API keys)
        - Uses dispatch.target for message delivery
        """
        target_user_id = job.dispatch.target.user_id
        target_session_id = job.dispatch.target.session_id
        dispatch_meta: Dict[str, Any] = dict(job.dispatch.meta or {})

        # For LLM calls, use the job creator's config
        # created_by defaults to target_user_id for backward compatibility
        config_user_id = job.created_by or target_user_id

        logger.info(
            "cron execute: job_id=%s channel=%s task_type=%s "
            "config_user_id=%s target_user_id=%s target_session_id=%s",
            job.id,
            job.dispatch.channel,
            job.task_type,
            config_user_id[:40] if config_user_id else "",
            target_user_id[:40] if target_user_id else "",
            target_session_id[:40] if target_session_id else "",
        )

        if job.task_type == "text" and job.text:
            logger.info(
                "cron send_text: job_id=%s channel=%s len=%s",
                job.id,
                job.dispatch.channel,
                len(job.text or ""),
            )
            await self._channel_manager.send_text(
                channel=job.dispatch.channel,
                user_id=target_user_id,
                session_id=target_session_id,
                text=job.text.strip(),
                meta=dispatch_meta,
            )
            return

        # agent: run request using the job creator's config for LLM
        # but send results to the dispatch target
        logger.info(
            "cron agent: job_id=%s channel=%s config_user=%s target=%s",
            job.id,
            job.dispatch.channel,
            config_user_id,
            target_user_id,
        )
        assert job.request is not None
        req: Dict[str, Any] = job.request.model_dump(mode="json")
        # Use config_user_id for LLM config loading
        req["user_id"] = config_user_id or "cron"
        # Use target_session_id for session management
        req["session_id"] = target_session_id or f"cron:{job.id}"

        async def _run() -> None:
            async for event in self._runner.stream_query(req):
                await self._channel_manager.send_event(
                    channel=job.dispatch.channel,
                    user_id=target_user_id,  # Send to target user
                    session_id=target_session_id,
                    event=event,
                    meta=dispatch_meta,
                )

        await asyncio.wait_for(_run(), timeout=job.runtime.timeout_seconds)
