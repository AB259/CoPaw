# 供应商全量分发功能设计

## Context

当前系统已有两种分发功能：
- `POST /models/distribution/active-llm` - 分发单个 provider + active_model 到目标租户
- `POST /mcp/distribute/default-agents` - 分发选中的 MCP clients

供应商（providers）配置按租户隔离存储于 `~/.swe.secret/<tenant_id>/providers/`，包含：
- `builtin/` - 内置 provider 配置文件
- `custom/` - 自定义 provider 配置文件
- `active_model.json` - 当前激活的模型配置

用户需要从某个租户全量分发整个 providers 目录到多个目标租户，实现配置的统一覆盖。

## Goals / Non-Goals

**Goals:**
- P0：新增 `POST /models/distribution/providers` 端点，支持全量覆盖分发
- P1：分发整个 providers 目录（builtin/、custom/、active_model.json）
- P2：自动初始化目标租户，确保分发后立即可用
- P3：复用现有的 tenant listing、bootstrap 模式，保持一致性

**Non-Goals:**
- 不修改现有分发端点的行为
- 不支持增量合并分发（只做全量覆盖）
- 不支持选择性分发（指定部分 providers）
- 不支持跨 source 分发

## Decisions

### D1: 新增独立端点 `/models/distribution/providers`

**选择：** 在 `providers.py` 新增独立端点，与现有 `active-llm` 分发端点并列。

**替代方案：** 扩展现有端点增加 `mode` 参数 → 参数结构和返回结构差异大，逻辑复杂。

**理由：**
- 单 provider 分发需要 `provider_id` 参数，全量分发不需要
- 返回结构不同：单 provider 分发返回 `provider_updated`，全量分发返回整体成功状态
- 独立端点语义清晰，易于理解和维护

### D2: 目录级复制，使用 `shutil.copytree`

**选择：** 直接复制整个 providers 目录，先删除目标目录再复制。

**替代方案：** 遍历文件逐个复制 → 代码复杂，与现有模式不一致。

**理由：**
- 与 `TenantInitializer.seed_providers_from_default()` 已有实现模式一致
- 全量覆盖语义下，目录级复制更直观可靠
- 代码量少、易于维护

### D3: 分发前自动初始化目标租户

**选择：** 分发前调用 `TenantInitializer.ensure_seeded_bootstrap()`，确保目标租户目录存在。

**替代方案：** 仅分发已存在租户，未初始化返回错误 → 与现有分发行为不一致，用户体验差。

**理由：**
- 与现有 MCP 分发、active-llm 分发行为保持一致
- 确保分发后目标租户立即可用，无需额外初始化步骤

### D4: 分发内容包含敏感信息（api_key）

**选择：** 全量复制 providers 目录，包含 api_key 等敏感信息。

**替代方案：** 仅分发非敏感配置，目标租户需自行配置 API Key → 用户确认需要 A。

**理由：**
- 用户需求是"直接覆盖用户的 providers 目录"，即完整配置分发
- 分发场景通常在受控环境内，租户间信任关系明确
- 分发后目标租户可立即使用，无需额外配置步骤

## API Design

### Endpoint

```
POST /models/distribution/providers
```

### Request

```python
class ProvidersDistributionRequest(BaseModel):
    target_tenant_ids: List[str] = Field(
        default_factory=list,
        description="Target tenant IDs to distribute providers to",
    )
    overwrite: bool = Field(
        ...,
        description="Must be true for providers distribution",
    )
```

### Response

```python
class ProvidersDistributionTenantResult(BaseModel):
    tenant_id: str = Field(..., description="Target tenant ID")
    success: bool = Field(..., description="Whether distribution succeeded")
    bootstrapped: bool = Field(
        default=False,
        description="Whether the target tenant was bootstrapped during distribution",
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")

class ProvidersDistributionResponse(BaseModel):
    source_tenant_id: str = Field(..., description="Source tenant ID")
    results: List[ProvidersDistributionTenantResult] = Field(
        default_factory=list,
        description="Per-tenant distribution results",
    )
```

### Behavior

1. **参数校验：**
   - `overwrite` 必须为 `True`，否则返回 400 错误
   - `target_tenant_ids` 不能为空，否则返回 400 错误

2. **获取源目录：**
   - 从请求上下文获取 `effective_tenant_id`
   - 源目录：`SECRET_DIR / effective_tenant_id / "providers"`
   - 若源目录不存在，返回 400 错误

3. **遍历目标租户：**
   - 验证 `tenant_id` 格式（防路径穿越）
   - 调用 `TenantInitializer.ensure_seeded_bootstrap()` 初始化
   - 删除目标 providers 目录（如果存在）
   - 复制源 providers 目录到目标位置

4. **错误处理：**
   - 单个租户失败不影响其他租户
   - 返回结果包含每个租户的成功/失败状态

## Implementation

### File Changes

| File | Change |
|------|--------|
| `src/swe/app/routers/providers.py` | 新增请求/响应模型、分发端点、辅助函数 |

### Core Implementation

```python
# 新增模型定义
class ProvidersDistributionRequest(BaseModel):
    target_tenant_ids: List[str] = Field(default_factory=list)
    overwrite: bool = Field(...)

class ProvidersDistributionTenantResult(BaseModel):
    tenant_id: str
    success: bool
    bootstrapped: bool = False
    error: Optional[str] = None

class ProvidersDistributionResponse(BaseModel):
    source_tenant_id: str
    results: List[ProvidersDistributionTenantResult]

# 新增端点
@router.post(
    "/distribution/providers",
    response_model=ProvidersDistributionResponse,
    summary="Distribute entire providers directory to target tenants",
)
async def distribute_providers(
    request: Request,
    body: ProvidersDistributionRequest = Body(...),
) -> ProvidersDistributionResponse:
    # 实现逻辑
    ...

# 新增辅助函数
async def _distribute_providers_to_tenant(
    *,
    source_providers_dir: Path,
    target_tenant_id: str,
    source_working_dir: Path,
    source_id: str | None,
) -> ProvidersDistributionTenantResult:
    # 实现逻辑
    ...
```

### Distribution Flow

```
validate_request()
    ↓
get_source_providers_dir()
    ↓
for each target_tenant_id:
    ├── validate_tenant_id()
    ├── TenantInitializer.ensure_seeded_bootstrap()
    ├── get_target_providers_dir()
    ├── if exists: shutil.rmtree()
    └── shutil.copytree(source, target)
    ↓
return ProvidersDistributionResponse
```

## Testing

### Unit Tests

| Test Case | Description |
|-----------|-------------|
| `test_distribute_providers_success` | 成功分发到单个租户 |
| `test_distribute_providers_multiple_tenants` | 成功分发到多个租户 |
| `test_distribute_providers_overwrite_required` | overwrite=False 返回 400 |
| `test_distribute_providers_empty_tenants` | 空 tenant_ids 返回 400 |
| `test_distribute_providers_source_not_exists` | 源目录不存在返回 400 |
| `test_distribute_providers_partial_failure` | 部分租户失败不影响其他 |
| `test_distribute_providers_bootstraps_tenant` | 自动初始化未存在的租户 |

### Integration Tests

- 验证分发后目标租户可正常使用 provider 配置
- 验证 `active_model.json` 正确复制
- 验证自定义 providers 正确复制

## Risks / Trade-offs

- **[R1] 敏感信息分发** → 分发包含 api_key，需确保在受控环境内使用。依赖现有 K8s 网络策略保护。
- **[R2] 目标目录并发写入** → 采用目录级复制，无锁。极低概率竞争，与现有行为一致。
- **[R3] 大规模分发性能** → 同步遍历租户，大量租户时可能耗时较长。可接受，与现有分发行为一致。
