# -*- coding: utf-8 -*-
"""market 内部使用的租户上下文与 tenant 解析工具。"""

from __future__ import annotations

import base64
import logging
import shutil
from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

_LEGACY_SCOPE_ID_PREFIX = "scope.v1"
_IDENTITY_MAX_LENGTH = 256

current_tenant_id: ContextVar[str | None] = ContextVar(
    "market_current_tenant_id",
    default=None,
)
current_user_id: ContextVar[str | None] = ContextVar(
    "market_current_user_id",
    default=None,
)
current_workspace_dir: ContextVar[Path | None] = ContextVar(
    "market_current_workspace_dir",
    default=None,
)
current_source_id: ContextVar[str | None] = ContextVar(
    "market_current_source_id",
    default=None,
)


def is_valid_identity_value(identity: str) -> bool:
    """按主服务规则校验 tenant/source 原始身份值。"""
    if not identity:
        return False
    if len(identity) < 1 or len(identity) > _IDENTITY_MAX_LENGTH:
        return False
    if ".." in identity or "/" in identity or "\\" in identity:
        return False
    if any(ord(char) < 32 for char in identity):
        return False
    return True


def _encode_scope_component(value: str) -> str:
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode(
        "ascii",
    )
    return encoded.rstrip("=")


def _decode_scope_component(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(
        (value + padding).encode("ascii"),
    ).decode("utf-8")


def encode_scope_id(tenant_id: str, source_id: str) -> str:
    """按主服务一致规则编码运行时 scope 标识。"""
    if not is_valid_identity_value(tenant_id):
        raise ValueError("Invalid tenant_id for scope encoding")
    if not is_valid_identity_value(source_id):
        raise ValueError("Invalid source_id for scope encoding")
    return ".".join(
        (
            _encode_scope_component(tenant_id),
            _encode_scope_component(source_id),
        ),
    )


def decode_scope_id(scope_id: str) -> tuple[str, str]:
    """兼容新旧 scope 目录格式，返回逻辑 tenant/source。"""
    prefix = f"{_LEGACY_SCOPE_ID_PREFIX}."
    payload = (
        scope_id[len(prefix) :] if scope_id.startswith(prefix) else scope_id
    )
    parts = payload.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Invalid scope_id payload")
    return (
        _decode_scope_component(parts[0]),
        _decode_scope_component(parts[1]),
    )


def canonicalize_scope_id(scope_id: str) -> str:
    """把 legacy scope 统一收敛为 canonical 无前缀格式。"""
    tenant_id, source_id = decode_scope_id(scope_id)
    return encode_scope_id(tenant_id, source_id)


def resolve_effective_tenant_id(
    tenant_id: str,
    source_id: str | None,
) -> str:
    """解析 market 本地状态使用的运行时 scope 标识。"""
    if not source_id:
        try:
            return canonicalize_scope_id(tenant_id)
        except ValueError:
            return tenant_id
    return encode_scope_id(tenant_id, source_id)


def _merge_legacy_scope_directory(source_dir: Path, target_dir: Path) -> None:
    """把 legacy 目录中的文件合并到 canonical 目录。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    for source_path in source_dir.iterdir():
        target_path = target_dir / source_path.name
        if source_path.is_dir():
            if target_path.exists():
                _merge_legacy_scope_directory(source_path, target_path)
                continue
            try:
                source_path.rename(target_path)
            except OSError:
                shutil.copytree(source_path, target_path)
                shutil.rmtree(source_path)
            continue

        if target_path.exists():
            source_path.unlink()
            continue

        try:
            source_path.rename(target_path)
        except OSError:
            shutil.copy2(source_path, target_path)
            source_path.unlink()

    source_dir.rmdir()


def migrate_legacy_scope_dir_if_needed(base_dir: Path, tenant_id: str) -> Path:
    """按需把 legacy scope 目录迁移到 canonical 目录。"""
    try:
        canonical_scope_id = canonicalize_scope_id(tenant_id)
    except ValueError:
        return base_dir / tenant_id

    canonical_dir = base_dir / canonical_scope_id
    legacy_dir = base_dir / f"{_LEGACY_SCOPE_ID_PREFIX}.{canonical_scope_id}"

    if not legacy_dir.exists():
        return canonical_dir

    if not canonical_dir.exists():
        try:
            legacy_dir.rename(canonical_dir)
            logger.info(
                "Migrated legacy scope dir: %s -> %s",
                legacy_dir,
                canonical_dir,
            )
            return canonical_dir
        except OSError:
            logger.warning(
                "Atomic legacy scope migration failed, merging instead: %s -> %s",
                legacy_dir,
                canonical_dir,
            )

    _merge_legacy_scope_directory(legacy_dir, canonical_dir)
    logger.info("Merged legacy scope dir: %s -> %s", legacy_dir, canonical_dir)
    return canonical_dir


@contextmanager
def tenant_context(
    tenant_id: str | None = None,
    user_id: str | None = None,
    workspace_dir: Path | None = None,
    source_id: str | None = None,
) -> Generator[None, None, None]:
    """在当前协程上下文中临时绑定租户信息。"""
    tokens: list[tuple[ContextVar, Token]] = []
    try:
        if tenant_id is not None:
            tokens.append(
                (current_tenant_id, current_tenant_id.set(tenant_id)),
            )
        if user_id is not None:
            tokens.append((current_user_id, current_user_id.set(user_id)))
        if workspace_dir is not None:
            tokens.append(
                (
                    current_workspace_dir,
                    current_workspace_dir.set(workspace_dir),
                ),
            )
        if source_id is not None:
            tokens.append(
                (current_source_id, current_source_id.set(source_id)),
            )
        yield
    finally:
        for context_var, token in reversed(tokens):
            context_var.reset(token)
