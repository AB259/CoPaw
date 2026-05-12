# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from .models import (
    CommandHookHandlerConfig,
    FailPolicy,
    HookContext,
    HookDecision,
    HookHandlerConfig,
    HookHandlerResult,
    HttpHookHandlerConfig,
)
from .output import normalize_hook_output
from .redaction import redact_hook_payload

logger = logging.getLogger(__name__)


async def execute_handler(
    handler: HookHandlerConfig,
    context: HookContext,
    *,
    workspace_dir: Path,
) -> HookHandlerResult:
    logger.debug(
        "Executing hook handler id=%s type=%s context=%s",
        handler.id,
        handler.type,
        redact_hook_payload(context.to_handler_payload()),
    )
    try:
        if isinstance(handler, CommandHookHandlerConfig):
            return await _execute_command_handler(
                handler,
                context,
                workspace_dir,
            )
        if isinstance(handler, HttpHookHandlerConfig):
            return await _execute_http_handler(handler, context)
    except asyncio.TimeoutError:
        return _failure(handler, "Hook handler timed out", "timeout")
    except Exception as exc:
        return _failure(handler, str(exc), "execution_error")
    return _failure(handler, "Unsupported hook handler type", "unsupported")


async def _execute_command_handler(
    handler: CommandHookHandlerConfig,
    context: HookContext,
    workspace_dir: Path,
) -> HookHandlerResult:
    cwd = _resolve_hook_cwd(handler.cwd, workspace_dir)
    env = os.environ.copy()
    env.update(handler.env)
    payload = json.dumps(
        context.to_handler_payload(),
        ensure_ascii=False,
    ).encode()

    if handler.argv:
        _validate_argv_boundaries(handler.argv, workspace_dir)
        proc = await asyncio.create_subprocess_exec(
            *handler.argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
        )
    else:
        proc = await asyncio.create_subprocess_shell(
            handler.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
        )

    stdout, stderr = await asyncio.wait_for(
        proc.communicate(payload),
        timeout=handler.timeout,
    )
    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode == 0:
        if not stdout_text:
            raw: dict[str, Any] = {}
        else:
            try:
                raw = json.loads(stdout_text)
            except json.JSONDecodeError as exc:
                return _failure(
                    handler,
                    f"Invalid hook JSON output: {exc}",
                    "invalid_output",
                )
            if not isinstance(raw, dict):
                return _failure(
                    handler,
                    "Hook JSON output must be an object",
                    "invalid_output",
                )
        return normalize_hook_output(
            handler_id=handler.id,
            order=0,
            raw_output=raw,
        )

    if proc.returncode == 2:
        reason = stderr_text or handler.status_message or "Hook blocked event"
        return HookHandlerResult(
            handler_id=handler.id,
            order=0,
            decision=HookDecision.BLOCK,
            reason=reason,
        )

    reason = stderr_text or f"Hook command exited with code {proc.returncode}"
    return _failure(handler, reason, "non_zero_exit")


async def _execute_http_handler(
    handler: HttpHookHandlerConfig,
    context: HookContext,
) -> HookHandlerResult:
    headers = _build_http_headers(handler, context.effective_tenant_id)
    try:
        async with httpx.AsyncClient(timeout=handler.timeout) as client:
            response = await client.post(
                handler.url,
                json=context.to_handler_payload(),
                headers=headers,
            )
    except httpx.TimeoutException:
        return _failure(handler, "HTTP hook timed out", "timeout")
    except httpx.HTTPError as exc:
        return _failure(handler, f"HTTP hook failed: {exc}", "http_error")

    text = response.text.strip() if response.text else ""
    if 200 <= response.status_code < 300:
        if not text:
            raw: dict[str, Any] = {}
        else:
            try:
                raw = response.json()
            except json.JSONDecodeError as exc:
                return _failure(
                    handler,
                    f"Invalid hook JSON output: {exc}",
                    "invalid_output",
                )
            if not isinstance(raw, dict):
                return _failure(
                    handler,
                    "Hook JSON output must be an object",
                    "invalid_output",
                )
        return normalize_hook_output(
            handler_id=handler.id,
            order=0,
            raw_output=raw,
        )

    if response.status_code in {409, 422}:
        if text:
            try:
                raw = response.json()
            except json.JSONDecodeError:
                raw = {}
            if isinstance(raw, dict) and raw:
                parsed = normalize_hook_output(
                    handler_id=handler.id,
                    order=0,
                    raw_output=raw,
                )
                if parsed.decision != HookDecision.NONE:
                    return parsed
        return HookHandlerResult(
            handler_id=handler.id,
            order=0,
            decision=HookDecision.BLOCK,
            reason=text or handler.status_message or "HTTP hook blocked event",
        )

    return _failure(
        handler,
        f"HTTP hook returned status {response.status_code}",
        "http_status",
    )


def _resolve_hook_cwd(raw_cwd: str, workspace_dir: Path) -> Path:
    root = workspace_dir.expanduser().resolve()
    candidate = Path(raw_cwd).expanduser() if raw_cwd else root
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Hook cwd is outside tenant workspace") from exc
    return resolved


def _validate_argv_boundaries(argv: list[str], workspace_dir: Path) -> None:
    root = workspace_dir.expanduser().resolve()
    for item in argv[1:]:
        path = Path(item).expanduser()
        if not path.is_absolute() or not path.exists():
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(
                "Hook command path is outside tenant workspace",
            ) from exc


def _build_http_headers(
    handler: HttpHookHandlerConfig,
    tenant_id: str | None,
) -> dict[str, str]:
    headers = dict(handler.headers)
    if handler.header_secret_refs:
        try:
            from swe.config.utils import get_tenant_env
        except Exception:
            get_tenant_env = None
        if get_tenant_env is not None:
            for header_name, secret_name in handler.header_secret_refs.items():
                value = get_tenant_env(secret_name, tenant_id=tenant_id)
                if value is not None:
                    headers[header_name] = value
    for env_name in handler.allowed_env_vars:
        if env_name in os.environ:
            headers[env_name] = os.environ[env_name]
    return headers


def _failure(
    handler: HookHandlerConfig,
    reason: str,
    failure_type: str,
) -> HookHandlerResult:
    decision = (
        HookDecision.BLOCK
        if handler.fail_policy == FailPolicy.BLOCK
        else HookDecision.NONE
    )
    return HookHandlerResult(
        handler_id=handler.id,
        order=0,
        decision=decision,
        reason=reason,
        failed=True,
        failure_type=failure_type,
    )
