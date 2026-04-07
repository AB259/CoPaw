# Findings & Decisions

## Requirements
来自用户请求：
- 根据已有分析结果，进一步确认多租户隔离中出现问题的地点
- 制定整改计划
- 核心关注点：ProviderManager 单例、模型配置隔离、回退路径安全

## Research Findings

### 1. ProviderManager 单例分析

**文件**: `src/copaw/providers/provider_manager.py`

ProviderManager 是全局单例模式：
```python
class ProviderManager:
    _instance = None

    @staticmethod
    def get_instance() -> "ProviderManager":
        if ProviderManager._instance is None:
            ProviderManager._instance = ProviderManager()
        return ProviderManager._instance
```

**存储位置**（全局共享）：
- `SECRET_DIR / "providers"` → `~/.copaw/.secret/providers/`
- `active_model.json` 存储全局默认模型配置

**状态**：⚠️ **潜在问题** - 虽然 ProviderManager 是单例，但实际模型选择优先使用 TenantModelContext

### 2. TenantModelManager 隔离机制（✅ 正确实现）

**文件**: `src/copaw/tenant_models/manager.py`

存储位置按租户隔离：
```python
@classmethod
def get_config_path(cls, tenant_id: str) -> Path:
    return SECRET_DIR / tenant_id / "tenant_models.json"
```

路径格式：`~/.copaw/.secret/{tenant_id}/tenant_models.json`

### 3. 模型选择回退路径分析

**文件**: `src/copaw/agents/model_factory.py` (第 754-775 行)

```python
# Try to get model from tenant-level configuration
try:
    from copaw.tenant_models import TenantModelContext

    tenant_config = TenantModelContext.get_config()
    if tenant_config:
        model_slot = tenant_config.get_active_slot()
except Exception:
    pass

# Create chat model from agent-specific or global config
if model_slot and model_slot.provider_id and model_slot.model:
    # Use agent-specific model (tenant-isolated)
    ...
else:
    # Fallback to global active model
    model = ProviderManager.get_active_chat_model()
```

**回退路径触发条件**：
1. `TenantModelContext.get_config()` 返回 None（租户未配置模型）
2. `tenant_config.get_active_slot()` 返回无效配置

**风险等级**: 🟡 **中等** - 当租户未配置模型时，会使用全局默认模型

### 4. TenantModelContext 设置路径

**HTTP 请求模式**（✅ 正确设置）：
- 文件：`src/copaw/app/middleware/tenant_workspace.py` (第 100-103 行)
- `TenantWorkspaceMiddleware` 在每个请求上设置 `TenantModelContext`

**Channel 消息模式**（✅ 正确设置）：
- 文件：`src/copaw/app/channels/base.py` (第 790-794 行)
- `_consume_one_request` 使用 `bind_tenant_context` 设置上下文

### 5. 潜在问题确认

#### 问题 1：全局默认模型共享（🟡 中等风险）

**问题描述**：
当租户未配置自己的模型时，系统回退到 `ProviderManager.get_active_chat_model()`，这会使用全局 `active_model.json` 中的配置。

**影响范围**：
- 多个未配置模型的租户共享同一个全局默认模型
- 如果全局模型配置被修改，会影响所有依赖回退的租户

**代码位置**：
- `src/copaw/agents/model_factory.py:767`

#### 问题 2：ProviderManager active_model 竞争条件（🟡 低风险）

**问题描述**：
`ProviderManager.save_active_model()` 和 `load_active_model()` 操作全局文件，在多租户并发环境下可能存在竞争条件。

**代码位置**：
- `src/copaw/providers/provider_manager.py:944-969`

#### 问题 3：CLI 模式隔离一致性（🟢 已验证）

**验证结果**：
- CLI 模式通过 `copaw app --user-id <id>` 设置当前用户
- 使用 `bind_tenant_context` 绑定上下文
- 模型选择逻辑与 HTTP 模式一致

### 6. 实际隔离效果验证

| 隔离维度 | 状态 | 说明 |
|----------|------|------|
| 目录隔离 | ✅ | `~/.copaw/{tenant_id}/` 独立目录 |
| 配置隔离 | ✅ | 租户独立 config.json |
| Agent 隔离 | ✅ | `{tenant_id}:{agent_id}` 缓存键 |
| 模型配置隔离 | ⚠️ | 依赖 TenantModelContext，回退时共享全局 |
| 请求上下文 | ✅ | contextvars 正确实现 |

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| 确认 ProviderManager 单例不是问题根源 | TenantModelContext 提供了正确的隔离层 |
| 回退路径需要整改 | 避免未配置租户共享全局模型 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 全局 active_model.json 被共享 | 需要为每个租户提供独立默认模型 |
| 回退路径未考虑租户隔离 | 需要修改 model_factory 逻辑 |

## 整改计划

### 整改项 1：模型选择回退路径优化

**目标**：确保即使租户未配置模型，也不会意外共享全局配置

**方案 A：强制租户配置（推荐）**
- 修改 `model_factory.py` 第 765-775 行
- 当 `TenantModelContext.get_config()` 返回 None 时，抛出错误而不是回退到全局
- 要求每个租户必须配置自己的模型

**方案 B：租户级默认模型**
- 当租户未配置模型时，使用系统预设的默认模型（而非 ProviderManager 的 active_model）
- 在 `TenantModelManager` 中提供 `get_or_create_default()` 方法

### 整改项 2：ProviderManager active_model 访问控制

**目标**：防止意外的全局模型修改影响多租户环境

**方案**：
- 添加警告日志当 `ProviderManager.get_active_chat_model()` 被调用时
- 在 `_app.py` 初始化时，如果检测到多租户模式，禁止修改全局 active_model

### 整改项 3：TenantModelContext 完整性检查

**目标**：确保模型选择前 TenantModelContext 已正确设置

**方案**：
- 在 `model_factory.py` 添加检查，如果上下文未设置且无法获取，抛出明确错误
- 添加 `TenantModelContext.is_configured()` 辅助方法

### 整改项 4：测试覆盖

**目标**：验证整改后的隔离行为

**测试用例**：
1. 测试未配置模型的租户行为
2. 测试全局模型修改是否影响其他租户
3. 测试并发场景下的模型选择

## Resources
- 项目根目录: `/Users/shixiangyi/code/CoPaw`
- ProviderManager: `src/copaw/providers/provider_manager.py`
- TenantModelManager: `src/copaw/tenant_models/manager.py`
- Model Factory: `src/copaw/agents/model_factory.py`
- Tenant Workspace Middleware: `src/copaw/app/middleware/tenant_workspace.py`

## 结论

**确认的问题地点**：
1. ✅ `src/copaw/agents/model_factory.py:767` - 模型选择回退路径
2. ✅ `src/copaw/providers/provider_manager.py:579` - 全局存储路径
3. ✅ `src/copaw/providers/provider_manager.py:944-969` - active_model 读写

**整改优先级**：
1. 🟡 高：模型选择回退路径优化（方案 A 或 B）
2. 🟢 中：ProviderManager active_model 访问控制
3. 🟢 中：TenantModelContext 完整性检查
4. 🟢 低：测试覆盖

**推荐方案**：实施整改项 1（方案 A：强制租户配置），确保多租户隔离的完整性。
