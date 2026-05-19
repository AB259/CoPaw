# -*- coding: utf-8 -*-
"""Source 级系统配置模型与默认值。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceSystemConfig(BaseModel):
    """Source 系统配置载荷，业务 key 由具体使用方自行约定。"""

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def _validate_object(cls, data: Any) -> Any:
        """只接受 JSON object，避免数组或标量让调用方语义不明确。"""
        if not isinstance(data, dict):
            raise ValueError("source system config must be a JSON object")
        return data

    def as_dict(self) -> dict[str, Any]:
        """返回普通 dict，供合并默认配置和序列化使用。"""
        return self.model_dump(mode="json")

    def merged_with_defaults(self) -> "SourceSystemConfig":
        """将 source 覆盖合并到内置默认配置。"""
        return SourceSystemConfig.model_validate(
            {
                **DEFAULT_SOURCE_SYSTEM_CONFIG.as_dict(),
                **self.as_dict(),
            },
        )


DEFAULT_SOURCE_SYSTEM_CONFIG = SourceSystemConfig()


class SourceSystemConfigRecord(BaseModel):
    """Source 系统配置持久化记录。"""

    source_id: str = Field(..., min_length=1, max_length=64)
    config: SourceSystemConfig
    version: int = Field(default=1, ge=1)
    updated_by: str | None = Field(default=None, max_length=128)
    updated_at: datetime | None = None


class EffectiveSourceSystemConfig(BaseModel):
    """运行时合成后的 source 系统配置。"""

    source_id: str = Field(..., min_length=1, max_length=64)
    config: SourceSystemConfig
    version: int = Field(default=0, ge=0)
    is_default: bool = False
    stale: bool = False
    last_error: str | None = None
    updated_by: str | None = Field(default=None, max_length=128)
    updated_at: datetime | None = None


class SourceSystemConfigUpsert(BaseModel):
    """Source 系统配置创建或更新请求。"""

    model_config = ConfigDict(extra="forbid")

    config: SourceSystemConfig
    updated_by: str | None = Field(default=None, max_length=128)
