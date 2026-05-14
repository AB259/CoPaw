# 供应商全量分发功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `POST /models/distribution/providers` 端点，支持从当前租户全量分发 providers 目录到多个目标租户。

**Architecture:** 采用目录级复制方式（`shutil.copytree`），复用现有的 `TenantInitializer` 进行租户初始化，与现有 `active-llm` 分发端点并列。

**Tech Stack:** FastAPI, Pydantic, pathlib, shutil

---

## File Structure

| File | Action | Description |
|------|--------|-------------|
| `src/swe/app/routers/providers.py` | Modify | 新增请求/响应模型、分发端点、辅助函数 |
| `tests/unit/routers/test_providers_distribution.py` | Create | 单元测试 |

---

### Task 1: 新增请求/响应模型

**Files:**
- Modify: `src/swe/app/routers/providers.py`

- [ ] **Step 1: 在 providers.py 中新增 ProvidersDistributionRequest 模型**

在 `ActiveModelDistributionResponse` 模型定义之后，添加新的模型定义：

```python
class ProvidersDistributionRequest(BaseModel):
    """Request body for distributing entire providers directory."""

    target_tenant_ids: List[str] = Field(
        default_factory=list,
        description="Target tenant IDs to distribute providers to",
    )
    overwrite: bool = Field(
        ...,
        description="Must be true for providers distribution",
    )


class ProvidersDistributionTenantResult(BaseModel):
    """Per-tenant providers distribution result."""

    tenant_id: str = Field(..., description="Target tenant ID")
    success: bool = Field(..., description="Whether distribution succeeded")
    bootstrapped: bool = Field(
        default=False,
        description="Whether the target tenant was bootstrapped during distribution",
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ProvidersDistributionResponse(BaseModel):
    """Response payload for providers distribution requests."""

    source_tenant_id: str = Field(..., description="Source tenant ID")
    results: List[ProvidersDistributionTenantResult] = Field(
        default_factory=list,
        description="Per-tenant distribution results",
    )
```

- [ ] **Step 2: 验证语法正确**

Run: `python -c "from swe.app.routers import providers; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/swe/app/routers/providers.py
git commit -m "$(cat <<'EOF'
feat(providers): add request/response models for providers distribution

Add ProvidersDistributionRequest, ProvidersDistributionTenantResult,
and ProvidersDistributionResponse models for the new
POST /models/distribution/providers endpoint.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: 新增辅助函数

**Files:**
- Modify: `src/swe/app/routers/providers.py`

- [ ] **Step 1: 在 providers.py 中添加必要的导入**

在文件顶部的导入区域，确认 `shutil` 和 `Path` 已导入。找到 `from pathlib import Path` 或类似位置，添加：

```python
import shutil
```

确认 `SECRET_DIR` 已从 `swe.constant` 导入。如果没有，在导入区域添加：

```python
from ...constant import SECRET_DIR
```

- [ ] **Step 2: 新增 _get_effective_tenant_id 辅助函数**

在 `_request_source_id` 函数之后，添加：

```python
def _get_effective_tenant_id(request: Request) -> str | None:
    """Get effective tenant ID from request context."""
    from ...config.context import resolve_effective_tenant_id

    tenant_id = _request_tenant_id(request)
    if tenant_id is None:
        return None
    return resolve_effective_tenant_id(tenant_id, _request_source_id(request))
```

- [ ] **Step 3: 新增 _distribute_providers_to_tenant 辅助函数**

在 `_get_effective_tenant_id` 函数之后，添加：

```python
def _distribute_providers_to_tenant(
    *,
    source_providers_dir: Path,
    target_tenant_id: str,
    source_working_dir: Path,
    source_id: str | None,
) -> ProvidersDistributionTenantResult:
    """Distribute providers directory to a single target tenant.

    Args:
        source_providers_dir: Source tenant's providers directory path.
        target_tenant_id: Target tenant ID.
        source_working_dir: Source tenant's working directory parent.
        source_id: Source identifier for tenant initialization.

    Returns:
        Distribution result for this tenant.
    """
    initializer = TenantInitializer(
        source_working_dir.parent,
        target_tenant_id,
        source_id=source_id,
    )
    was_bootstrapped = initializer.has_seeded_bootstrap()
    if not was_bootstrapped:
        initializer.ensure_seeded_bootstrap()

    target_providers_dir = SECRET_DIR / target_tenant_id / "providers"

    # Remove existing target directory if exists
    if target_providers_dir.exists():
        shutil.rmtree(target_providers_dir)

    # Copy entire providers directory
    shutil.copytree(source_providers_dir, target_providers_dir)

    return ProvidersDistributionTenantResult(
        tenant_id=target_tenant_id,
        success=True,
        bootstrapped=not was_bootstrapped,
    )
```

- [ ] **Step 4: 验证语法正确**

Run: `python -c "from swe.app.routers import providers; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/swe/app/routers/providers.py
git commit -m "$(cat <<'EOF'
feat(providers): add helper functions for providers distribution

Add _get_effective_tenant_id and _distribute_providers_to_tenant
helper functions to support the providers distribution endpoint.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: 新增分发端点

**Files:**
- Modify: `src/swe/app/routers/providers.py`

- [ ] **Step 1: 在 providers.py 中新增 distribute_providers 端点**

在 `distribute_active_model` 端点之后、`tenant_providers_router` 定义之前，添加：

```python
@router.post(
    "/distribution/providers",
    response_model=ProvidersDistributionResponse,
    summary="Distribute entire providers directory to target tenants",
)
async def distribute_providers(
    request: Request,
    body: ProvidersDistributionRequest = Body(...),
) -> ProvidersDistributionResponse:
    """Copy entire providers directory from current tenant to target tenants.

    This endpoint performs a full overwrite of the target tenants' providers
    directory, including builtin/, custom/, and active_model.json.

    Args:
        request: FastAPI request object.
        body: Distribution request with target tenant IDs.

    Returns:
        Distribution results for each target tenant.

    Raises:
        HTTPException: 400 if overwrite is False, no target tenants provided,
            or source providers directory doesn't exist.
    """
    if not body.overwrite:
        raise HTTPException(
            status_code=400,
            detail="overwrite=true is required for providers distribution",
        )
    if not body.target_tenant_ids:
        raise HTTPException(
            status_code=400,
            detail="No target tenant IDs provided",
        )

    # Get source tenant's effective tenant ID
    effective_tenant_id = _get_effective_tenant_id(request)
    if effective_tenant_id is None:
        raise HTTPException(
            status_code=400,
            detail="No tenant ID in request context",
        )

    # Get source providers directory
    source_providers_dir = SECRET_DIR / effective_tenant_id / "providers"
    if not source_providers_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Source providers directory not found for tenant '{effective_tenant_id}'",
        )

    source_working_dir = _request_tenant_working_dir(request)
    source_id = _request_source_id(request)

    results: list[ProvidersDistributionTenantResult] = []
    for tenant_id in body.target_tenant_ids:
        try:
            validated_tenant_id = _validate_target_tenant_id(tenant_id)
            result = _distribute_providers_to_tenant(
                source_providers_dir=source_providers_dir,
                target_tenant_id=validated_tenant_id,
                source_working_dir=source_working_dir,
                source_id=source_id,
            )
            results.append(result)
        except Exception as exc:
            results.append(
                ProvidersDistributionTenantResult(
                    tenant_id=str(tenant_id),
                    success=False,
                    error=str(exc),
                ),
            )

    return ProvidersDistributionResponse(
        source_tenant_id=effective_tenant_id,
        results=results,
    )
```

- [ ] **Step 2: 验证语法正确**

Run: `python -c "from swe.app.routers import providers; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/swe/app/routers/providers.py
git commit -m "$(cat <<'EOF'
feat(providers): add POST /models/distribution/providers endpoint

Add endpoint to distribute entire providers directory from current
tenant to multiple target tenants with full overwrite support.
Supports auto-bootstrap of target tenants before distribution.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: 编写单元测试

**Files:**
- Create: `tests/unit/routers/test_providers_distribution.py`

- [ ] **Step 1: 创建测试文件并编写基础测试**

```python
# -*- coding: utf-8 -*-
"""Providers distribution router tests."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from swe.app.routers import providers as providers_router


def _request(
    tenant_id: str = "tenant-source",
    source_id: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(tenant_id=tenant_id, source_id=source_id),
    )


def _setup_source_providers(
    secret_dir: Path,
    tenant_id: str,
) -> Path:
    """Create a source providers directory with sample content."""
    providers_dir = secret_dir / tenant_id / "providers"
    providers_dir.mkdir(parents=True, exist_ok=True)

    # Create builtin directory with a sample provider
    builtin_dir = providers_dir / "builtin"
    builtin_dir.mkdir(exist_ok=True)
    builtin_provider = builtin_dir / "openai.json"
    builtin_provider.write_text(
        '{"id": "openai", "name": "OpenAI", "api_key": "sk-test", "base_url": "https://api.openai.com/v1", "models": [{"id": "gpt-4", "name": "GPT-4"}], "extra_models": [], "chat_model": "OpenAIChatModel"}',
        encoding="utf-8",
    )

    # Create custom directory with a sample custom provider
    custom_dir = providers_dir / "custom"
    custom_dir.mkdir(exist_ok=True)
    custom_provider = custom_dir / "custom-llm.json"
    custom_provider.write_text(
        '{"id": "custom-llm", "name": "Custom LLM", "api_key": "custom-key", "base_url": "https://custom.example/v1", "models": [{"id": "custom-model", "name": "Custom Model"}], "extra_models": [], "chat_model": "OpenAIChatModel", "is_custom": true}',
        encoding="utf-8",
    )

    # Create active_model.json
    active_model_file = providers_dir / "active_model.json"
    active_model_file.write_text(
        '{"provider_id": "openai", "model": "gpt-4"}',
        encoding="utf-8",
    )

    return providers_dir


def test_distribute_providers_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test successful distribution to a single tenant."""
    secret_dir = tmp_path / "secret"
    source_providers_dir = _setup_source_providers(secret_dir, "tenant-source")

    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "get_tenant_working_dir_strict",
        lambda tenant_id: tmp_path / str(tenant_id),
    )

    class FakeInitializer:
        def __init__(
            self,
            _base_working_dir: Path,
            tenant_id: str,
            source_id: str | None = None,
        ):
            self.tenant_id = tenant_id

        def has_seeded_bootstrap(self) -> bool:
            return True

        def ensure_seeded_bootstrap(self) -> dict[str, Any]:
            return {"minimal": True}

    monkeypatch.setattr(providers_router, "TenantInitializer", FakeInitializer)

    result = asyncio.run(
        providers_router.distribute_providers(
            _request(),
            providers_router.ProvidersDistributionRequest(
                target_tenant_ids=["tenant-target"],
                overwrite=True,
            ),
        ),
    )

    assert result.source_tenant_id == "tenant-source"
    assert len(result.results) == 1
    assert result.results[0].tenant_id == "tenant-target"
    assert result.results[0].success is True
    assert result.results[0].bootstrapped is False

    # Verify target directory was created
    target_providers_dir = secret_dir / "tenant-target" / "providers"
    assert target_providers_dir.exists()
    assert (target_providers_dir / "builtin" / "openai.json").exists()
    assert (target_providers_dir / "custom" / "custom-llm.json").exists()
    assert (target_providers_dir / "active_model.json").exists()


def test_distribute_providers_multiple_tenants(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test successful distribution to multiple tenants."""
    secret_dir = tmp_path / "secret"
    _setup_source_providers(secret_dir, "tenant-source")

    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "get_tenant_working_dir_strict",
        lambda tenant_id: tmp_path / str(tenant_id),
    )

    class FakeInitializer:
        def __init__(
            self,
            _base_working_dir: Path,
            tenant_id: str,
            source_id: str | None = None,
        ):
            self.tenant_id = tenant_id

        def has_seeded_bootstrap(self) -> bool:
            return True

        def ensure_seeded_bootstrap(self) -> dict[str, Any]:
            return {"minimal": True}

    monkeypatch.setattr(providers_router, "TenantInitializer", FakeInitializer)

    result = asyncio.run(
        providers_router.distribute_providers(
            _request(),
            providers_router.ProvidersDistributionRequest(
                target_tenant_ids=["tenant-a", "tenant-b"],
                overwrite=True,
            ),
        ),
    )

    assert len(result.results) == 2
    assert all(r.success for r in result.results)
    assert [r.tenant_id for r in result.results] == ["tenant-a", "tenant-b"]


def test_distribute_providers_overwrite_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that overwrite=False returns 400 error."""
    secret_dir = tmp_path / "secret"
    _setup_source_providers(secret_dir, "tenant-source")

    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "get_tenant_working_dir_strict",
        lambda tenant_id: tmp_path / str(tenant_id),
    )

    with pytest.raises(providers_router.HTTPException) as exc_info:
        asyncio.run(
            providers_router.distribute_providers(
                _request(),
                providers_router.ProvidersDistributionRequest(
                    target_tenant_ids=["tenant-target"],
                    overwrite=False,
                ),
            ),
        )

    assert exc_info.value.status_code == 400
    assert "overwrite=true" in str(exc_info.value.detail)


def test_distribute_providers_empty_tenants(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that empty target_tenant_ids returns 400 error."""
    secret_dir = tmp_path / "secret"
    _setup_source_providers(secret_dir, "tenant-source")

    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "get_tenant_working_dir_strict",
        lambda tenant_id: tmp_path / str(tenant_id),
    )

    with pytest.raises(providers_router.HTTPException) as exc_info:
        asyncio.run(
            providers_router.distribute_providers(
                _request(),
                providers_router.ProvidersDistributionRequest(
                    target_tenant_ids=[],
                    overwrite=True,
                ),
            ),
        )

    assert exc_info.value.status_code == 400
    assert "No target tenant IDs" in str(exc_info.value.detail)


def test_distribute_providers_source_not_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that missing source providers directory returns 400 error."""
    secret_dir = tmp_path / "secret"
    # Do NOT create source providers directory

    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "get_tenant_working_dir_strict",
        lambda tenant_id: tmp_path / str(tenant_id),
    )

    with pytest.raises(providers_router.HTTPException) as exc_info:
        asyncio.run(
            providers_router.distribute_providers(
                _request(),
                providers_router.ProvidersDistributionRequest(
                    target_tenant_ids=["tenant-target"],
                    overwrite=True,
                ),
            ),
        )

    assert exc_info.value.status_code == 400
    assert "Source providers directory not found" in str(exc_info.value.detail)


def test_distribute_providers_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that partial failure doesn't affect other tenants."""
    secret_dir = tmp_path / "secret"
    _setup_source_providers(secret_dir, "tenant-source")

    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "get_tenant_working_dir_strict",
        lambda tenant_id: tmp_path / str(tenant_id),
    )

    call_count = 0

    class FakeInitializer:
        def __init__(
            self,
            _base_working_dir: Path,
            tenant_id: str,
            source_id: str | None = None,
        ):
            self.tenant_id = tenant_id

        def has_seeded_bootstrap(self) -> bool:
            return True

        def ensure_seeded_bootstrap(self) -> dict[str, Any]:
            return {"minimal": True}

    original_rmtree = shutil.rmtree

    def mock_rmtree(path, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call (tenant-a) succeeds
            return original_rmtree(path, *args, **kwargs)
        # Second call (tenant-b) fails
        raise OSError("Simulated failure")

    monkeypatch.setattr(providers_router, "TenantInitializer", FakeInitializer)
    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

    result = asyncio.run(
        providers_router.distribute_providers(
            _request(),
            providers_router.ProvidersDistributionRequest(
                target_tenant_ids=["tenant-a", "tenant-b"],
                overwrite=True,
            ),
        ),
    )

    assert len(result.results) == 2
    assert result.results[0].success is True
    assert result.results[1].success is False
    assert "Simulated failure" in str(result.results[1].error)


def test_distribute_providers_bootstraps_tenant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that unbootstrapped tenant gets initialized."""
    secret_dir = tmp_path / "secret"
    _setup_source_providers(secret_dir, "tenant-source")

    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "get_tenant_working_dir_strict",
        lambda tenant_id: tmp_path / str(tenant_id),
    )

    bootstrap_calls: list[str] = []

    class FakeInitializer:
        def __init__(
            self,
            _base_working_dir: Path,
            tenant_id: str,
            source_id: str | None = None,
        ):
            self.tenant_id = tenant_id

        def has_seeded_bootstrap(self) -> bool:
            return False

        def ensure_seeded_bootstrap(self) -> dict[str, Any]:
            bootstrap_calls.append(self.tenant_id)
            return {"minimal": True}

    monkeypatch.setattr(providers_router, "TenantInitializer", FakeInitializer)

    result = asyncio.run(
        providers_router.distribute_providers(
            _request(),
            providers_router.ProvidersDistributionRequest(
                target_tenant_ids=["tenant-new"],
                overwrite=True,
            ),
        ),
    )

    assert bootstrap_calls == ["tenant-new"]
    assert result.results[0].bootstrapped is True
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd "D:\Vibe Coding\CoPaw1.0.0\CoPaw" && venv/Scripts/python -m pytest tests/unit/routers/test_providers_distribution.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/unit/routers/test_providers_distribution.py
git commit -m "$(cat <<'EOF'
test(providers): add unit tests for providers distribution endpoint

Add tests for:
- Successful distribution to single/multiple tenants
- Validation errors (overwrite, empty tenants, missing source)
- Partial failure handling
- Auto-bootstrap of unbootstrapped tenants

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: 集成验证

**Files:**
- No file changes

- [ ] **Step 1: 运行完整测试套件**

Run: `cd "D:\Vibe Coding\CoPaw1.0.0\CoPaw" && venv/Scripts/python -m pytest tests/unit/routers/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: 运行 providers 相关测试**

Run: `cd "D:\Vibe Coding\CoPaw1.0.0\CoPaw" && venv/Scripts/python -m pytest tests/unit/providers/ tests/unit/routers/test_provider* -v`
Expected: All tests pass

---

## Self-Review

### Spec Coverage

| Spec Requirement | Task |
|------------------|------|
| P0: 新增 POST /models/distribution/providers 端点 | Task 3 |
| P1: 分发整个 providers 目录 | Task 2, Task 3 |
| P2: 自动初始化目标租户 | Task 2 |
| P3: 复用 tenant listing、bootstrap 模式 | Task 2, Task 3 |
| overwrite 必须为 True | Task 3, Task 4 (test) |
| target_tenant_ids 不能为空 | Task 3, Task 4 (test) |
| 源目录不存在返回 400 | Task 3, Task 4 (test) |
| 部分失败不影响其他 | Task 2, Task 4 (test) |

### Placeholder Scan

- ✅ 无 TBD/TODO
- ✅ 所有代码步骤包含完整实现代码
- ✅ 所有测试步骤包含完整测试代码
- ✅ 无模糊描述

### Type Consistency

- ✅ `ProvidersDistributionRequest.target_tenant_ids: List[str]` 与 `_validate_target_tenant_id` 返回 `str` 一致
- ✅ `ProvidersDistributionTenantResult` 定义与使用一致
- ✅ `ProvidersDistributionResponse.source_tenant_id: str` 与 `effective_tenant_id` 类型一致
