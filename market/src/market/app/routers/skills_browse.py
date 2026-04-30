# -*- coding: utf-8 -*-
"""用户市场浏览 API 和我的技能 API."""
import asyncio
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile

from ...marketplace.fs import get_user_skills_dir
from ...marketplace.schemas import (
    MarketSkillDetail,
    MarketSkillResponse,
    MySkillItem,
)
from ..deps import require_source_id

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_ZIP_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}


async def _read_validated_zip_upload(file: UploadFile) -> bytes:
    """Validate and read uploaded zip file."""
    if file.content_type and file.content_type not in _ALLOWED_ZIP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Expected a zip file, "
                f"got content-type: {file.content_type}"
            ),
        )

    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large ({len(data) // (1024 * 1024)} MB). "
                f"Maximum is {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            ),
        )
    return data


def _find_skill_candidates(zf: zipfile.ZipFile) -> set[str]:
    """Find skill directories in zip file."""
    candidates: set[str] = set()
    for name in zf.namelist():
        normalized = name.replace("\\", "/")
        parts = normalized.split("/")
        if len(parts) >= 2 and parts[-1] in ("skill.json", "SKILL.md"):
            candidates.add(parts[0])
    return candidates


def _extract_skill_files(
    zf: zipfile.ZipFile,
    skill_name: str,
    skill_dir: Path,
) -> dict[str, Any]:
    """Extract skill files from zip and return skill.json data."""
    skill_data: dict[str, Any] = {}
    prefix = f"{skill_name}/"
    for member in zf.namelist():
        normalized = member.replace("\\", "/")
        if not normalized.startswith(prefix):
            continue
        rel_path = normalized[len(prefix) :]
        if not rel_path:  # Skip directory itself
            continue
        target_path = skill_dir / rel_path
        if member.endswith("/"):
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            content = zf.read(member)
            target_path.write_bytes(content)
            if rel_path == "skill.json":
                try:
                    skill_data = json.loads(content.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
    return skill_data


def _import_single_skill(
    zf: zipfile.ZipFile,
    skill_name: str,
    skills_dir: Path,
    user_id: str,
    user_name: str,
    bbk_id: str,
    overwrite: bool,
    target_name: str,
) -> tuple[str | None, dict[str, str] | None]:
    """Import a single skill from zip. Returns (imported_name, conflict_info)."""
    final_name = target_name or skill_name
    skill_dir = skills_dir / final_name

    if skill_dir.exists() and not overwrite:
        return None, {
            "reason": "already_exists",
            "skill_name": final_name,
            "suggested_name": f"{final_name}_1",
        }

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_data = _extract_skill_files(zf, skill_name, skill_dir)

    skill_data["source"] = "customized"
    skill_data["creator_id"] = user_id
    skill_data["creator_name"] = user_name
    skill_data["bbk_id"] = bbk_id

    (skill_dir / "skill.json").write_text(
        json.dumps(skill_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return final_name, None


def _import_skill_from_zip(
    skills_dir: Path,
    data: bytes,
    user_id: str,
    user_name: str,
    bbk_id: str,
    overwrite: bool = False,
    target_name: str = "",
) -> dict[str, Any]:
    """Import skill from zip data to user skills directory."""
    imported: list[str] = []
    conflicts: list[dict[str, str]] = []

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            skill_candidates = _find_skill_candidates(zf)
            if not skill_candidates:
                raise HTTPException(
                    status_code=400,
                    detail="No valid skill found in zip (missing skill.json or SKILL.md)",
                )

            for skill_name in skill_candidates:
                name, conflict = _import_single_skill(
                    zf,
                    skill_name,
                    skills_dir,
                    user_id,
                    user_name,
                    bbk_id,
                    overwrite,
                    target_name,
                )
                if name:
                    imported.append(name)
                elif conflict:
                    conflicts.append(conflict)

    except zipfile.BadZipFile as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid zip file: {e}",
        ) from e

    result = {"imported": imported, "count": len(imported)}
    if conflicts:
        result["conflicts"] = conflicts
    return result


@router.get("/market/skills", response_model=list[MarketSkillResponse])
async def list_skills(
    request: Request,
    category_id: Optional[int] = None,
    x_source_id: Optional[str] = Header(default=None, alias="X-Source-Id"),
    x_bbk_id: Optional[str] = Header(default=None, alias="X-Bbk-Id"),
):
    """浏览市场技能列表（按 source_id + bbk_id 过滤）."""
    source_id = require_source_id(x_source_id)
    user_bbk_id = x_bbk_id or "100"
    svc = request.app.state.marketplace
    return await svc.list_skills(
        source_id,
        user_bbk_id,
        category_id=category_id,
    )


@router.get("/market/skills/mine", response_model=list[MySkillItem])
async def get_my_skills(
    request: Request,
    x_source_id: Optional[str] = Header(default=None, alias="X-Source-Id"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    agent_id: str = "default",
):
    """我创建的技能列表."""
    source_id = require_source_id(x_source_id)
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header is required",
        )
    svc = request.app.state.marketplace
    all_skills = await svc.get_my_skills(source_id, x_user_id, agent_id)
    return [s for s in all_skills if not s.is_received]


@router.get("/market/skills/received", response_model=list[MySkillItem])
async def get_received_skills(
    request: Request,
    x_source_id: Optional[str] = Header(default=None, alias="X-Source-Id"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    agent_id: str = "default",
):
    """我接收的技能列表."""
    source_id = require_source_id(x_source_id)
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header is required",
        )
    svc = request.app.state.marketplace
    all_skills = await svc.get_my_skills(source_id, x_user_id, agent_id)
    return [s for s in all_skills if s.is_received]


@router.get("/market/skills/{item_id}", response_model=MarketSkillDetail)
async def get_skill_detail(
    item_id: str,
    request: Request,
    x_source_id: Optional[str] = Header(default=None, alias="X-Source-Id"),
    x_bbk_id: Optional[str] = Header(default=None, alias="X-Bbk-Id"),
):
    """预览技能详情."""
    source_id = require_source_id(x_source_id)
    user_bbk_id = x_bbk_id or "100"
    svc = request.app.state.marketplace
    detail = await svc.get_skill_detail(source_id, item_id, user_bbk_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return detail


@router.post("/market/skills/upload")
async def upload_skill_to_workspace(
    request: Request,
    file: UploadFile = File(..., description="Skill zip file to upload"),
    x_source_id: Optional[str] = Header(default=None, alias="X-Source-Id"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_user_name: Optional[str] = Header(default=None, alias="X-User-Name"),
    x_bbk_id: Optional[str] = Header(default=None, alias="X-Bbk-Id"),
    enable: bool = True,
    overwrite: bool = False,
    target_name: str = "",
):
    """上传技能到工作区，记录 user_id, bbk_id, user_name."""
    source_id = require_source_id(x_source_id)
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header is required",
        )

    svc = request.app.state.marketplace
    swe_root = svc.swe_root
    user_name = x_user_name or x_user_id
    bbk_id = x_bbk_id or "100"
    agent_id = "default"

    # Get user skills directory
    skills_dir = get_user_skills_dir(swe_root, x_user_id, agent_id)
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Read and validate zip
    data = await _read_validated_zip_upload(file)

    # Import skill
    result = await asyncio.to_thread(
        _import_skill_from_zip,
        skills_dir,
        data,
        x_user_id,
        user_name,
        bbk_id,
        overwrite=overwrite,
        target_name=target_name,
    )

    # Log upload operation
    if svc.db.is_connected and result.get("imported"):
        try:
            await svc.db.execute(
                """
                INSERT INTO swe_marketplace_operation_logs
                    (source_id, operator_id, operator_name, operation,
                     item_type, item_id, item_name,
                     target_user_id, target_user_name, target_bbk_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    source_id,
                    x_user_id,
                    user_name,
                    "upload",
                    "skill",
                    "",
                    ",".join(result["imported"]),
                    x_user_id,
                    user_name,
                    bbk_id,
                ),
            )
        except Exception as e:
            logger.warning("Failed to log upload operation: %s", e)

    result["enabled"] = enable
    return result
