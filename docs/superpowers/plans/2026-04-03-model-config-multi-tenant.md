# 模型配置多租户隔离实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现模型配置的多租户隔离，每个租户拥有独立的模型配置文件，Agent 自动使用所属租户的配置

**Architecture:** 基于配置文件存储（非数据库），创建独立的 tenant_models 模块处理租户级别模型配置，通过 ContextVar 绑定到请求上下文，API 自动返回当前租户的 provider 列表

**Tech Stack:** Python, Pydantic, FastAPI, pytest

---

## 文件结构

```
src/copaw/tenant_models/
├── __init__.py          # 模块导出
├── models.py            # Pydantic 数据模型
├── manager.py           # 配置加载/保存/缓存管理
├── context.py           # 上下文绑定工具
├── exceptions.py        # 自定义异常
└── utils.py             # 工具函数（环境变量解析等）

tests/unit/tenant_models/
├── test_models.py       # 模型验证测试
├── test_manager.py      # 管理器测试
└── test_context.py      # 上下文测试

tests/integration/
└── test_tenant_model_api.py  # API 集成测试
```

---

## Task 1: 创建异常类

**Files:**
- Create: `src/copaw/tenant_models/exceptions.py`
- Test: `tests/unit/tenant_models/test_exceptions.py`

- [ ] **Step 1: 编写异常测试**

```python
# tests/unit/tenant_models/test_exceptions.py
def test_tenant_model_not_found_error():
    from copaw.tenant_models.exceptions import TenantModelNotFoundError

    error = TenantModelNotFoundError("tenant1")
    assert str(error) == "Tenant model config not found for tenant: tenant1"
    assert error.tenant_id == "tenant1"

def test_tenant_model_provider_error():
    from copaw.tenant_models.exceptions import TenantModelProviderError

    error = TenantModelProviderError("provider1", "API key missing")
    assert "provider1" in str(error)
    assert "API key missing" in str(error)
    assert error.provider_id == "provider1"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/tenant_models/test_exceptions.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'copaw.tenant_models'"

- [ ] **Step 3: 创建异常类**

```python
# src/copaw/tenant_models/exceptions.py
"""Exceptions for tenant model configuration."""


class TenantModelError(RuntimeError):
    """Base exception for tenant model errors."""

    pass


class TenantModelNotFoundError(TenantModelError):
    """Raised when tenant model configuration is not found."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant model config not found for tenant: {tenant_id}")


class TenantModelProviderError(TenantModelError):
    """Raised when provider instantiation fails."""

    def __init__(self, provider_id: str, message: str):
        self.provider_id = provider_id
        super().__init__(f"Provider '{provider_id}' error: {message}")


class TenantModelValidationError(TenantModelError):
    """Raised when configuration validation fails."""

    pass
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/tenant_models/test_exceptions.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/tenant_models/test_exceptions.py src/copaw/tenant_models/exceptions.py
git commit -m "feat(tenant_models): add exception classes"
```

---

## Task 2: 创建数据模型

**Files:**
- Create: `src/copaw/tenant_models/models.py`
- Test: `tests/unit/tenant_models/test_models.py`

- [ ] **Step 1: 编写模型测试**

```python
# tests/unit/tenant_models/test_models.py
import pytest
from pydantic import ValidationError


def test_tenant_provider_config():
    from copaw.tenant_models.models import TenantProviderConfig

    config = TenantProviderConfig(
        id="openai_tenant",
        type="openai",
        api_key="${ENV:OPENAI_API_KEY}",
        base_url="https://api.openai.com/v1",
        models=["gpt-5", "gpt-5.2"],
        enabled=True,
    )

    assert config.id == "openai_tenant"
    assert config.type == "openai"
    assert config.api_key == "${ENV:OPENAI_API_KEY}"
    assert config.models == ["gpt-5", "gpt-5.2"]
    assert config.enabled is True


def test_tenant_provider_config_defaults():
    from copaw.tenant_models.models import TenantProviderConfig

    config = TenantProviderConfig(id="minimal", type="openai")

    assert config.api_key is None
    assert config.base_url is None
    assert config.models == []
    assert config.enabled is True
    assert config.extra == {}


def test_model_slot():
    from copaw.tenant_models.models import ModelSlot

    slot = ModelSlot(provider_id="openai_tenant", model="gpt-5")
    assert slot.provider_id == "openai_tenant"
    assert slot.model == "gpt-5"


def test_routing_config():
    from copaw.tenant_models.models import RoutingConfig, ModelSlot

    config = RoutingConfig(
        mode="local_first",
        slots={
            "local": ModelSlot(provider_id="local_p", model="local-model"),
            "cloud": ModelSlot(provider_id="cloud_p", model="cloud-model"),
        },
    )
    assert config.mode == "local_first"
    assert "local" in config.slots
    assert "cloud" in config.slots


def test_routing_config_invalid_mode():
    from copaw.tenant_models.models import RoutingConfig, ModelSlot

    with pytest.raises(ValidationError):
        RoutingConfig(
            mode="invalid_mode",  # Should be local_first or cloud_first
            slots={"local": ModelSlot(provider_id="p", model="m")},
        )


def test_tenant_model_config_get_active_slot_local_first():
    from copaw.tenant_models.models import TenantModelConfig, RoutingConfig, ModelSlot

    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={
                "local": ModelSlot(provider_id="local_p", model="local-model"),
                "cloud": ModelSlot(provider_id="cloud_p", model="cloud-model"),
            },
        )
    )

    active = config.get_active_slot()
    assert active.provider_id == "local_p"
    assert active.model == "local-model"


def test_tenant_model_config_get_active_slot_cloud_first():
    from copaw.tenant_models.models import TenantModelConfig, RoutingConfig, ModelSlot

    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="cloud_first",
            slots={
                "local": ModelSlot(provider_id="local_p", model="local-model"),
                "cloud": ModelSlot(provider_id="cloud_p", model="cloud-model"),
            },
        )
    )

    active = config.get_active_slot()
    assert active.provider_id == "cloud_p"
    assert active.model == "cloud-model"


def test_tenant_model_config_get_other_slot():
    from copaw.tenant_models.models import TenantModelConfig, RoutingConfig, ModelSlot

    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={
                "local": ModelSlot(provider_id="local_p", model="local-model"),
                "cloud": ModelSlot(provider_id="cloud_p", model="cloud-model"),
            },
        )
    )

    other = config.get_other_slot()
    assert other.provider_id == "cloud_p"
    assert other.model == "cloud-model"


def test_tenant_model_config_version_default():
    from copaw.tenant_models.models import TenantModelConfig, RoutingConfig, ModelSlot

    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={
                "local": ModelSlot(provider_id="p", model="m"),
            },
        )
    )
    assert config.version == "1.0"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/tenant_models/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'copaw.tenant_models.models'"

- [ ] **Step 3: 创建数据模型**

```python
# src/copaw/tenant_models/models.py
"""Pydantic models for tenant model configuration."""
from typing import Dict, List, Literal, Optional, Any

from pydantic import BaseModel, Field


class TenantProviderConfig(BaseModel):
    """租户级别 Provider 配置."""

    id: str = Field(..., description="Provider 唯一标识")
    type: Literal["openai", "anthropic", "ollama"] = Field(
        ..., description="Provider 类型"
    )
    api_key: Optional[str] = Field(default=None, description="API Key（支持 ${ENV:XXX} 格式）")
    base_url: Optional[str] = Field(default=None, description="自定义 API 基础 URL")
    models: List[str] = Field(default_factory=list, description="支持的模型列表")
    enabled: bool = Field(default=True, description="是否启用")
    extra: Dict[str, Any] = Field(default_factory=dict, description="额外参数")


class ModelSlot(BaseModel):
    """模型槽位配置."""

    provider_id: str = Field(..., description="引用的 Provider ID")
    model: str = Field(..., description="模型名称")


class RoutingConfig(BaseModel):
    """路由配置."""

    mode: Literal["local_first", "cloud_first"] = Field(
        ..., description="路由策略: local_first 或 cloud_first"
    )
    slots: Dict[str, ModelSlot] = Field(
        ..., description="模型槽位配置 (local/cloud)"
    )


class TenantModelConfig(BaseModel):
    """租户模型配置根模型."""

    version: str = Field(default="1.0", description="配置版本")
    providers: List[TenantProviderConfig] = Field(
        default_factory=list, description="Provider 列表"
    )
    routing: RoutingConfig = Field(..., description="路由配置")

    def get_active_slot(self) -> ModelSlot:
        """根据 routing.mode 返回活跃槽位."""
        slot_key = self.routing.mode.replace("_first", "")
        return self.routing.slots[slot_key]

    def get_other_slot(self) -> ModelSlot:
        """返回另一个槽位（用于降级）."""
        current_key = self.routing.mode.replace("_first", "")
        other_key = "cloud" if current_key == "local" else "local"
        return self.routing.slots[other_key]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/tenant_models/test_models.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/tenant_models/test_models.py src/copaw/tenant_models/models.py
git commit -m "feat(tenant_models): add data models"
```

---

## Task 3: 创建工具函数

**Files:**
- Create: `src/copaw/tenant_models/utils.py`
- Test: `tests/unit/tenant_models/test_utils.py`

- [ ] **Step 1: 编写工具函数测试**

```python
# tests/unit/tenant_models/test_utils.py
import os


def test_resolve_env_vars_with_env_var():
    from copaw.tenant_models.utils import resolve_env_vars

    os.environ["TEST_API_KEY"] = "secret123"
    try:
        result = resolve_env_vars("${ENV:TEST_API_KEY}")
        assert result == "secret123"
    finally:
        del os.environ["TEST_API_KEY"]


def test_resolve_env_vars_without_env_var():
    from copaw.tenant_models.utils import resolve_env_vars

    result = resolve_env_vars("${ENV:NON_EXISTENT_VAR}")
    assert result == ""


def test_resolve_env_vars_plain_string():
    from copaw.tenant_models.utils import resolve_env_vars

    result = resolve_env_vars("plain_value")
    assert result == "plain_value"


def test_resolve_env_vars_none():
    from copaw.tenant_models.utils import resolve_env_vars

    result = resolve_env_vars(None)
    assert result is None


def test_resolve_env_vars_empty():
    from copaw.tenant_models.utils import resolve_env_vars

    result = resolve_env_vars("")
    assert result == ""


def test_resolve_env_vars_partial_env():
    """Test string with env var in middle."""
    from copaw.tenant_models.utils import resolve_env_vars

    os.environ["PARTIAL_VAR"] = "middle"
    try:
        result = resolve_env_vars("prefix_${ENV:PARTIAL_VAR}_suffix")
        assert result == "prefix_middle_suffix"
    finally:
        del os.environ["PARTIAL_VAR"]
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/tenant_models/test_utils.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'copaw.tenant_models.utils'"

- [ ] **Step 3: 创建工具函数**

```python
# src/copaw/tenant_models/utils.py
"""Utility functions for tenant model configuration."""
import os
import re
from typing import Optional


def resolve_env_vars(value: Optional[str]) -> Optional[str]:
    """解析字符串中的环境变量引用.

    支持格式: ${ENV:VAR_NAME}
    如果环境变量不存在，替换为空字符串.

    Args:
        value: 可能包含环境变量引用的字符串

    Returns:
        解析后的字符串，或原值（如果不包含环境变量引用）
    """
    if value is None:
        return None

    pattern = r"\$\{ENV:([^}]+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replacer, value)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/tenant_models/test_utils.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/tenant_models/test_utils.py src/copaw/tenant_models/utils.py
git commit -m "feat(tenant_models): add utility functions"
```

---

## Task 4: 创建配置管理器

**Files:**
- Create: `src/copaw/tenant_models/manager.py`
- Modify: `src/copaw/constant.py` (确认 WORKING_DIR 导出)
- Test: `tests/unit/tenant_models/test_manager.py`

- [ ] **Step 1: 编写管理器测试**

```python
# tests/unit/tenant_models/test_manager.py
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from copaw.tenant_models.models import TenantModelConfig, RoutingConfig, ModelSlot


@pytest.fixture
def temp_working_dir():
    """创建临时工作目录."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manager(temp_working_dir):
    """配置管理器 fixture."""
    from copaw.tenant_models import manager as mgr

    # 清理缓存
    mgr.TenantModelManager._cache.clear()

    with patch("copaw.tenant_models.manager.WORKING_DIR", temp_working_dir):
        yield mgr.TenantModelManager


def test_get_config_path(manager, temp_working_dir):
    path = manager.get_config_path("tenant1")
    expected = temp_working_dir / "tenants" / "tenant1" / "tenant_models.json"
    assert path == expected


def test_save_and_load_config(manager, temp_working_dir):
    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={
                "local": ModelSlot(provider_id="p1", model="m1"),
                "cloud": ModelSlot(provider_id="p2", model="m2"),
            },
        )
    )

    # 保存配置
    manager.save("tenant1", config)

    # 验证文件创建
    config_path = temp_working_dir / "tenants" / "tenant1" / "tenant_models.json"
    assert config_path.exists()

    # 加载配置
    loaded = manager.load("tenant1")
    assert loaded.routing.mode == "local_first"
    assert loaded.routing.slots["local"].provider_id == "p1"


def test_load_from_cache(manager, temp_working_dir):
    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="p1", model="m1")},
        )
    )

    # 保存并加载
    manager.save("tenant1", config)
    loaded1 = manager.load("tenant1")

    # 删除文件
    config_path = temp_working_dir / "tenants" / "tenant1" / "tenant_models.json"
    config_path.unlink()

    # 第二次加载应该从缓存获取
    loaded2 = manager.load("tenant1")
    assert loaded2 == loaded1


def test_load_fallback_to_default(manager, temp_working_dir):
    # 创建 default 配置
    default_config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="default_p", model="default_m")},
        )
    )
    manager.save("default", default_config)

    # 加载不存在的租户应该回退到 default
    loaded = manager.load("non_existent_tenant")
    assert loaded.routing.slots["local"].provider_id == "default_p"


def test_load_default_not_found(manager, temp_working_dir):
    from copaw.tenant_models.exceptions import TenantModelNotFoundError

    # 清理缓存
    manager._cache.clear()

    with pytest.raises(TenantModelNotFoundError) as exc_info:
        manager.load("default")

    assert "default" in str(exc_info.value)


def test_invalidate_cache_single(manager, temp_working_dir):
    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="p1", model="m1")},
        )
    )

    manager.save("tenant1", config)
    manager.load("tenant1")  # 填充缓存

    # 验证在缓存中
    assert "tenant1" in manager._cache

    # 使单个租户缓存失效
    manager.invalidate_cache("tenant1")
    assert "tenant1" not in manager._cache


def test_invalidate_cache_all(manager, temp_working_dir):
    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="p1", model="m1")},
        )
    )

    manager.save("tenant1", config)
    manager.save("tenant2", config)
    manager.load("tenant1")
    manager.load("tenant2")

    # 使所有缓存失效
    manager.invalidate_cache()
    assert len(manager._cache) == 0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/tenant_models/test_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'copaw.tenant_models.manager'"

- [ ] **Step 3: 创建配置管理器**

```python
# src/copaw/tenant_models/manager.py
"""Tenant model configuration manager."""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from copaw.constant import WORKING_DIR

from .exceptions import TenantModelNotFoundError, TenantModelProviderError
from .models import TenantModelConfig, ModelSlot

logger = logging.getLogger(__name__)


class TenantModelManager:
    """租户模型配置管理器.

    提供配置的加载、保存、缓存管理功能.
    """

    _cache: Dict[str, TenantModelConfig] = {}

    @classmethod
    def get_config_path(cls, tenant_id: str) -> Path:
        """获取租户配置文件路径.

        Args:
            tenant_id: 租户 ID

        Returns:
            配置文件路径
        """
        return Path(WORKING_DIR) / "tenants" / tenant_id / "tenant_models.json"

    @classmethod
    def load(cls, tenant_id: str) -> TenantModelConfig:
        """加载租户配置（带缓存）.

        Args:
            tenant_id: 租户 ID

        Returns:
            租户模型配置

        Raises:
            TenantModelNotFoundError: 如果 default 租户配置也不存在
        """
        if tenant_id in cls._cache:
            return cls._cache[tenant_id]

        config_path = cls.get_config_path(tenant_id)

        if not config_path.exists():
            if tenant_id == "default":
                raise TenantModelNotFoundError(tenant_id)

            # 降级到 default 租户
            logger.warning(
                f"Tenant {tenant_id} config not found at {config_path}, "
                f"falling back to default"
            )
            return cls.load("default")

        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)

        config = TenantModelConfig.model_validate(data)
        cls._cache[tenant_id] = config
        return config

    @classmethod
    def save(cls, tenant_id: str, config: TenantModelConfig) -> None:
        """保存租户配置.

        Args:
            tenant_id: 租户 ID
            config: 配置对象
        """
        config_path = cls.get_config_path(tenant_id)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)

        cls._cache[tenant_id] = config
        logger.info(f"Saved tenant model config for {tenant_id}")

    @classmethod
    def invalidate_cache(cls, tenant_id: Optional[str] = None) -> None:
        """使缓存失效.

        Args:
            tenant_id: 特定租户 ID，若为 None 则清除所有缓存
        """
        if tenant_id is None:
            cls._cache.clear()
            logger.debug("Invalidated all tenant model config cache")
        else:
            cls._cache.pop(tenant_id, None)
            logger.debug(f"Invalidated cache for tenant {tenant_id}")

    @classmethod
    def exists(cls, tenant_id: str) -> bool:
        """检查租户配置是否存在.

        Args:
            tenant_id: 租户 ID

        Returns:
            配置是否存在
        """
        return tenant_id in cls._cache or cls.get_config_path(tenant_id).exists()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/tenant_models/test_manager.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/tenant_models/test_manager.py src/copaw/tenant_models/manager.py
git commit -m "feat(tenant_models): add config manager"
```

---

## Task 5: 创建上下文绑定

**Files:**
- Create: `src/copaw/tenant_models/context.py`
- Modify: `src/copaw/config/context.py` (添加 tenant_model 相关导入)
- Test: `tests/unit/tenant_models/test_context.py`

- [ ] **Step 1: 编写上下文测试**

```python
# tests/unit/tenant_models/test_context.py
import pytest

from copaw.tenant_models.models import TenantModelConfig, RoutingConfig, ModelSlot


def test_set_and_get_config():
    from copaw.tenant_models.context import TenantModelContext

    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="p1", model="m1")},
        )
    )

    token = TenantModelContext.set_config(config)
    try:
        retrieved = TenantModelContext.get_config()
        assert retrieved == config
    finally:
        TenantModelContext.reset_config(token)


def test_get_config_not_set():
    from copaw.tenant_models.context import TenantModelContext

    # 确保上下文干净
    result = TenantModelContext.get_config()
    assert result is None


def test_get_config_strict_not_set():
    from copaw.tenant_models.context import TenantModelContext
    from copaw.config.context import TenantContextError

    with pytest.raises(TenantContextError):
        TenantModelContext.get_config_strict()


def test_get_config_strict_with_config():
    from copaw.tenant_models.context import TenantModelContext

    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="p1", model="m1")},
        )
    )

    token = TenantModelContext.set_config(config)
    try:
        result = TenantModelContext.get_config_strict()
        assert result == config
    finally:
        TenantModelContext.reset_config(token)


def test_reset_config():
    from copaw.tenant_models.context import TenantModelContext

    config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="p1", model="m1")},
        )
    )

    token = TenantModelContext.set_config(config)
    TenantModelContext.reset_config(token)

    # 重置后应该为 None
    result = TenantModelContext.get_config()
    assert result is None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/tenant_models/test_context.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'copaw.tenant_models.context'"

- [ ] **Step 3: 创建上下文绑定**

```python
# src/copaw/tenant_models/context.py
"""Tenant model configuration context utilities."""
from contextvars import ContextVar, Token
from typing import Optional

from copaw.config.context import TenantContextError

from .models import TenantModelConfig

# 上下文变量存储当前租户的模型配置
current_tenant_model_config: ContextVar[Optional[TenantModelConfig]] = ContextVar(
    "current_tenant_model_config",
    default=None,
)


class TenantModelContext:
    """租户模型配置上下文管理."""

    @staticmethod
    def set_config(config: TenantModelConfig) -> Token:
        """设置当前租户的模型配置.

        Args:
            config: 租户模型配置

        Returns:
            用于重置的 Token
        """
        return current_tenant_model_config.set(config)

    @staticmethod
    def get_config() -> Optional[TenantModelConfig]:
        """获取当前租户的模型配置.

        Returns:
            配置对象，若未设置则返回 None
        """
        return current_tenant_model_config.get()

    @staticmethod
    def get_config_strict() -> TenantModelConfig:
        """获取配置，若未设置则抛出错误.

        Returns:
            配置对象

        Raises:
            TenantContextError: 如果配置未设置
        """
        config = current_tenant_model_config.get()
        if config is None:
            raise TenantContextError(
                "Tenant model config not set in context. "
                "Ensure this code runs within a tenant-scoped request or context."
            )
        return config

    @staticmethod
    def reset_config(token: Token) -> None:
        """重置配置.

        Args:
            token: set_config 返回的 Token
        """
        current_tenant_model_config.reset(token)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/tenant_models/test_context.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/tenant_models/test_context.py src/copaw/tenant_models/context.py
git commit -m "feat(tenant_models): add context utilities"
```

---

## Task 6: 创建模块导出

**Files:**
- Create: `src/copaw/tenant_models/__init__.py`

- [ ] **Step 1: 创建模块导出**

```python
# src/copaw/tenant_models/__init__.py
"""Tenant model configuration module.

提供租户级别的模型配置管理功能.
"""

from .exceptions import (
    TenantModelError,
    TenantModelNotFoundError,
    TenantModelProviderError,
    TenantModelValidationError,
)
from .models import (
    ModelSlot,
    RoutingConfig,
    TenantModelConfig,
    TenantProviderConfig,
)
from .manager import TenantModelManager
from .context import TenantModelContext, current_tenant_model_config
from .utils import resolve_env_vars

__all__ = [
    # Exceptions
    "TenantModelError",
    "TenantModelNotFoundError",
    "TenantModelProviderError",
    "TenantModelValidationError",
    # Models
    "ModelSlot",
    "RoutingConfig",
    "TenantModelConfig",
    "TenantProviderConfig",
    # Manager
    "TenantModelManager",
    # Context
    "TenantModelContext",
    "current_tenant_model_config",
    # Utils
    "resolve_env_vars",
]
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from copaw.tenant_models import TenantModelConfig, TenantModelManager, TenantModelContext; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 3: 提交**

```bash
git add src/copaw/tenant_models/__init__.py
git commit -m "feat(tenant_models): add module exports"
```

---

## Task 7: 扩展中间件绑定租户模型配置

**Files:**
- Modify: `src/copaw/app/middleware/tenant_workspace.py`
- Test: `tests/unit/app/test_tenant_workspace.py` (更新现有测试)

- [ ] **Step 1: 更新中间件测试**

```python
# tests/unit/app/test_tenant_workspace.py - 添加以下测试
import pytest
from unittest.mock import patch, MagicMock


def test_middleware_loads_tenant_model_config():
    """测试中间件加载租户模型配置."""
    from copaw.app.middleware.tenant_workspace import TenantWorkspaceMiddleware
    from copaw.tenant_models import TenantModelConfig, RoutingConfig, ModelSlot

    # 创建模拟配置
    mock_config = TenantModelConfig(
        routing=RoutingConfig(
            mode="local_first",
            slots={"local": ModelSlot(provider_id="p1", model="m1")},
        )
    )

    with patch("copaw.app.middleware.tenant_workspace.TenantModelManager") as MockManager:
        MockManager.load.return_value = mock_config

        # 创建模拟请求和响应
        mock_request = MagicMock()
        mock_request.state.tenant_id = "tenant1"
        mock_request.app.state.tenant_workspace_pool = MagicMock()

        mock_response = MagicMock()

        async def mock_call_next(request):
            # 验证配置已绑定到上下文
            from copaw.tenant_models.context import TenantModelContext
            assert TenantModelContext.get_config() == mock_config
            return mock_response

        middleware = TenantWorkspaceMiddleware(MagicMock())

        import asyncio
        asyncio.run(middleware.dispatch(mock_request, mock_call_next))

        MockManager.load.assert_called_once_with("tenant1")
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/app/test_tenant_workspace.py::test_middleware_loads_tenant_model_config -v
```

Expected: FAIL because middleware doesn't call TenantModelManager yet

- [ ] **Step 3: 更新中间件代码**

```python
# src/copaw/app/middleware/tenant_workspace.py
# 在文件顶部添加导入
from ...tenant_models import TenantModelManager
from ...tenant_models.context import TenantModelContext

# 在 dispatch 方法中添加模型配置加载（在 workspace 加载之后）
async def dispatch(self, request: Request, call_next):
    # ... 现有代码 ...

    try:
        # 加载 workspace 如果 tenant_id 可用
        if tenant_id:
            workspace = await self._get_workspace(request, tenant_id)

            if workspace:
                # ... 现有 workspace 绑定代码 ...

                # 加载租户模型配置
                try:
                    tenant_model_config = TenantModelManager.load(tenant_id)
                    model_config_token = TenantModelContext.set_config(tenant_model_config)
                    logger.debug(
                        f"TenantWorkspaceMiddleware: loaded model config for tenant={tenant_id}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to load tenant model config: {e}")
                    model_config_token = None
            elif self._require_workspace:
                raise HTTPException(status_code=503, detail=...)

        # ... 调用下一个处理器 ...

    finally:
        # ... 现有 cleanup 代码 ...

        # 重置模型配置上下文
        if model_config_token:
            TenantModelContext.reset_config(model_config_token)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/app/test_tenant_workspace.py::test_middleware_loads_tenant_model_config -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/copaw/app/middleware/tenant_workspace.py tests/unit/app/test_tenant_workspace.py
git commit -m "feat(tenant_models): integrate model config into middleware"
```

---

## Task 8: 更新 API 端点

**Files:**
- Modify: `src/copaw/app/routers/providers.py` (或创建新的 router)
- Test: `tests/integration/test_tenant_model_api.py`

- [ ] **Step 1: 创建 API 测试**

```python
# tests/integration/test_tenant_model_api.py
import pytest
from unittest.mock import patch, MagicMock


def test_get_providers_returns_tenant_scoped_config(client):
    """测试获取 providers 返回租户限定配置."""
    from copaw.tenant_models import TenantModelConfig, RoutingConfig, ModelSlot, TenantProviderConfig

    mock_config = TenantModelConfig(
        providers=[
            TenantProviderConfig(id="p1", type="openai", api_key="key1", enabled=True),
        ],
        routing=RoutingConfig(
            mode="local_first",
            slots={
                "local": ModelSlot(provider_id="p1", model="gpt-5"),
            },
        ),
    )

    with patch("copaw.app.routers.providers.TenantModelManager.load") as mock_load:
        mock_load.return_value = mock_config

        response = client.get("/api/providers", headers={"X-Tenant-Id": "tenant1"})

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant1"
        assert len(data["providers"]) == 1
        assert data["providers"][0]["id"] == "p1"
        assert data["active_mode"] == "local_first"

        mock_load.assert_called_once_with("tenant1")
```

- [ ] **Step 2: 创建/更新 providers router**

```python
# src/copaw/app/routers/providers.py
"""Provider management endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ...config.context import get_current_tenant_id
from ...tenant_models import TenantModelManager

router = APIRouter()


@router.get("/api/providers")
async def get_providers(
    tenant_id: str = Depends(get_current_tenant_id),
):
    """获取当前租户的 provider 配置.

    Returns:
        租户模型配置信息
    """
    config = TenantModelManager.load(tenant_id)

    return {
        "tenant_id": tenant_id,
        "providers": [p.model_dump() for p in config.providers],
        "routing": config.routing.model_dump(),
        "active_mode": config.routing.mode,
        "active_slot": config.get_active_slot().model_dump(),
    }
```

- [ ] **Step 3: 运行测试验证通过**

```bash
pytest tests/integration/test_tenant_model_api.py -v
```

Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add tests/integration/test_tenant_model_api.py src/copaw/app/routers/providers.py
git commit -m "feat(api): add tenant-scoped providers endpoint"
```

---

## Task 9: 从 AgentProfileConfig 移除模型相关字段

**Files:**
- Modify: `src/copaw/config/config.py`
- Test: 验证 Agent 配置加载不受影响

- [ ] **Step 1: 查找并移除模型相关字段**

```python
# src/copaw/config/config.py
# 在 AgentProfileConfig 中移除以下字段:
# - active_model: Optional[ModelSlotConfig]
# - llm_routing: AgentsLLMRoutingConfig

# 注意: 需要保留这些字段的默认值以确保向后兼容
# 可以标记为 deprecated 并在未来版本移除
```

- [ ] **Step 2: 运行现有测试确保不破坏**

```bash
pytest tests/unit/config/ -v --tb=short
```

Expected: PASS (或显示需要更新的测试)

- [ ] **Step 3: 提交**

```bash
git add src/copaw/config/config.py
git commit -m "refactor(config): remove model config fields from AgentProfileConfig"
```

---

## Task 10: 创建迁移脚本

**Files:**
- Create: `scripts/migrate_to_tenant_models.py`

- [ ] **Step 1: 创建迁移脚本**

```python
#!/usr/bin/env python3
"""迁移脚本: 从旧的 providers.json 迁移到租户模型配置."""
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from copaw.constant import WORKING_DIR
from copaw.tenant_models import TenantModelConfig, TenantProviderConfig, RoutingConfig, ModelSlot
from copaw.tenant_models.manager import TenantModelManager


def load_old_providers_json():
    """加载旧的 providers.json."""
    old_path = Path(WORKING_DIR) / "providers.json"
    if not old_path.exists():
        print(f"No old config found at {old_path}")
        return None

    with open(old_path) as f:
        return json.load(f)


def migrate_provider(old_provider):
    """迁移单个 provider 配置."""
    return TenantProviderConfig(
        id=old_provider.get("id", old_provider.get("name", "unknown")),
        type=old_provider.get("type", "openai"),
        api_key=old_provider.get("api_key"),
        base_url=old_provider.get("base_url"),
        models=old_provider.get("models", []),
        enabled=old_provider.get("enabled", True),
        extra=old_provider.get("extra", {}),
    )


def main():
    """主迁移函数."""
    print("Starting migration to tenant model config...")

    old_config = load_old_providers_json()
    if old_config is None:
        print("Creating default config...")
        # 创建默认空配置
        config = TenantModelConfig(
            providers=[],
            routing=RoutingConfig(
                mode="local_first",
                slots={
                    "local": ModelSlot(provider_id="", model=""),
                    "cloud": ModelSlot(provider_id="", model=""),
                },
            ),
        )
    else:
        print(f"Migrating config from {Path(WORKING_DIR) / 'providers.json'}")
        providers = [migrate_provider(p) for p in old_config.get("providers", [])]

        # 尝试从旧配置推断路由设置
        old_routing = old_config.get("llm_routing", {})
        mode = old_routing.get("mode", "local_first")

        local_slot = ModelSlot(
            provider_id=old_routing.get("local", {}).get("provider_id", ""),
            model=old_routing.get("local", {}).get("model", ""),
        )
        cloud_slot = ModelSlot(
            provider_id=old_routing.get("cloud", {}).get("provider_id", ""),
            model=old_routing.get("cloud", {}).get("model", ""),
        )

        config = TenantModelConfig(
            providers=providers,
            routing=RoutingConfig(
                mode=mode,
                slots={"local": local_slot, "cloud": cloud_slot},
            ),
        )

    # 保存到 default 租户
    TenantModelManager.save("default", config)
    config_path = TenantModelManager.get_config_path("default")
    print(f"Migration complete! Config saved to: {config_path}")

    # 提示用户
    print("\nNext steps:")
    print("1. Review the migrated config at:", config_path)
    print("2. Update API keys if needed")
    print("3. Restart the application")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试迁移脚本**

```bash
python scripts/migrate_to_tenant_models.py
```

Expected: 创建默认配置或成功迁移现有配置

- [ ] **Step 3: 提交**

```bash
chmod +x scripts/migrate_to_tenant_models.py
git add scripts/migrate_to_tenant_models.py
git commit -m "feat(scripts): add migration script for tenant model config"
```

---

## 执行后验证

所有任务完成后，运行完整测试套件:

```bash
# 单元测试
pytest tests/unit/tenant_models/ -v

# 集成测试
pytest tests/integration/test_tenant_model_api.py -v

# 端到端测试（如果有）
pytest tests/e2e/ -v -k tenant_model
```

---

## 总结

本实现计划包含以下任务:

| 任务 | 描述 | 估计时间 |
|------|------|---------|
| Task 1 | 异常类 | 15 min |
| Task 2 | 数据模型 | 20 min |
| Task 3 | 工具函数 | 15 min |
| Task 4 | 配置管理器 | 25 min |
| Task 5 | 上下文绑定 | 20 min |
| Task 6 | 模块导出 | 10 min |
| Task 7 | 中间件集成 | 20 min |
| Task 8 | API 端点 | 20 min |
| Task 9 | Agent 配置清理 | 15 min |
| Task 10 | 迁移脚本 | 20 min |

**总计: ~3 小时**
