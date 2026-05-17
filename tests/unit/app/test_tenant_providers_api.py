# -*- coding: utf-8 -*-
"""Unit tests for tenant model API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import swe.app.routers.providers as providers_router
from swe.app.routers.providers import _distribute_providers_to_tenant
from swe.config.context import encode_scope_id, resolve_runtime_tenant_id
from swe.app.routers.providers import tenant_providers_router
from swe.tenant_models.models import (
    ModelSlot,
    RoutingConfig,
    TenantModelConfig,
    TenantProviderConfig,
)
from swe.tenant_models.exceptions import TenantModelNotFoundError


@pytest.fixture
def sample_tenant_config():
    """Create a sample TenantModelConfig for testing."""
    return TenantModelConfig(
        version="1.0",
        providers=[
            TenantProviderConfig(
                id="test-openai",
                type="openai",
                api_key="test-key",
                models=["gpt-4"],
                enabled=True,
            ),
        ],
        routing=RoutingConfig(
            mode="cloud_first",
            slots={
                "cloud": ModelSlot(provider_id="test-openai", model="gpt-4"),
                "local": ModelSlot(provider_id="test-ollama", model="llama2"),
            },
        ),
    )


@pytest.fixture
def client():
    """Create a TestClient for the tenant providers router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(tenant_providers_router)
    return TestClient(app)


class TestGetTenantProviders:
    """Tests for GET /providers endpoint."""

    def test_get_tenant_providers_success(self, client, sample_tenant_config):
        """Test successful retrieval of tenant configuration."""
        # Mock get_current_tenant_id to return a tenant ID
        with patch(
            "swe.app.routers.providers.get_current_tenant_id",
            return_value="test-tenant",
        ):
            # Mock TenantModelManager.load to return the sample config
            with patch(
                "swe.app.routers.providers.TenantModelManager.load",
                return_value=sample_tenant_config,
            ):
                response = client.get("/providers")

                assert response.status_code == 200
                data = response.json()

                # Verify response structure
                assert "tenant_id" in data
                assert "providers" in data
                assert "routing" in data
                assert "active_mode" in data
                assert "active_slot" in data

                # Verify content
                assert data["tenant_id"] == "test-tenant"
                assert len(data["providers"]) == 1
                assert data["providers"][0]["id"] == "test-openai"
                assert data["active_mode"] == "cloud_first"
                assert data["active_slot"]["provider_id"] == "test-openai"
                assert data["active_slot"]["model"] == "gpt-4"

    def test_get_tenant_providers_missing_tenant_id(self, client):
        """Test error when tenant ID is not set in context."""
        # Mock get_current_tenant_id to return None
        with patch(
            "swe.app.routers.providers.get_current_tenant_id",
            return_value=None,
        ):
            response = client.get("/providers")

            assert response.status_code == 400
            assert "Tenant ID not set" in response.json()["detail"]

    def test_get_tenant_providers_config_not_found(self, client):
        """Test error when tenant configuration is not found."""
        # Mock get_current_tenant_id to return a tenant ID
        with patch(
            "swe.app.routers.providers.get_current_tenant_id",
            return_value="nonexistent-tenant",
        ):
            # Mock TenantModelManager.load to raise TenantModelNotFoundError
            with patch(
                "swe.app.routers.providers.TenantModelManager.load",
                side_effect=TenantModelNotFoundError("nonexistent-tenant"),
            ):
                response = client.get("/providers")

                assert response.status_code == 404
                assert "Configuration not found" in response.json()["detail"]

    def test_get_tenant_providers_different_tenant(
        self,
        client,
        sample_tenant_config,
    ):
        """Test that different tenant IDs return different configurations."""
        tenant1_config = sample_tenant_config

        tenant2_config = TenantModelConfig(
            version="1.0",
            providers=[
                TenantProviderConfig(
                    id="tenant2-anthropic",
                    type="anthropic",
                    api_key="tenant2-key",
                    models=["claude-3"],
                    enabled=True,
                ),
            ],
            routing=RoutingConfig(
                mode="local_first",
                slots={
                    "local": ModelSlot(
                        provider_id="tenant2-ollama",
                        model="mistral",
                    ),
                    "cloud": ModelSlot(
                        provider_id="tenant2-anthropic",
                        model="claude-3",
                    ),
                },
            ),
        )

        # Test tenant1
        with patch(
            "swe.app.routers.providers.get_current_tenant_id",
            return_value="tenant1",
        ):
            with patch(
                "swe.app.routers.providers.TenantModelManager.load",
                return_value=tenant1_config,
            ):
                response1 = client.get("/providers")
                data1 = response1.json()

                assert data1["tenant_id"] == "tenant1"
                assert data1["providers"][0]["id"] == "test-openai"
                assert data1["active_mode"] == "cloud_first"

        # Test tenant2
        with patch(
            "swe.app.routers.providers.get_current_tenant_id",
            return_value="tenant2",
        ):
            with patch(
                "swe.app.routers.providers.TenantModelManager.load",
                return_value=tenant2_config,
            ):
                response2 = client.get("/providers")
                data2 = response2.json()

                assert data2["tenant_id"] == "tenant2"
                assert data2["providers"][0]["id"] == "tenant2-anthropic"
                assert data2["active_mode"] == "local_first"

                # Verify the two configurations are different
                assert data1 != data2


def test_distribute_providers_writes_target_source_scope(
    monkeypatch,
    tmp_path,
) -> None:
    """全量分发应写入目标 tenant + 当前 source 的 secret 命名空间。"""

    class FakeTenantInitializer:
        def __init__(self, base_working_dir, tenant_id, source_id=None):
            self.effective_tenant_id = resolve_runtime_tenant_id(
                tenant_id,
                source_id,
            )

        def has_seeded_bootstrap(self):
            return True

        def ensure_seeded_bootstrap(self):
            raise AssertionError("不应在已初始化租户上触发 bootstrap")

    secret_dir = tmp_path / ".swe.secret"
    source_providers_dir = tmp_path / "source" / "providers"
    source_providers_dir.mkdir(parents=True)
    (source_providers_dir / "active_model.json").write_text(
        '{"provider_id":"openai","model":"gpt-5"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(providers_router, "SECRET_DIR", secret_dir)
    monkeypatch.setattr(
        providers_router,
        "TenantInitializer",
        FakeTenantInitializer,
    )

    result = _distribute_providers_to_tenant(
        source_providers_dir=source_providers_dir,
        target_tenant_id="tenant-b",
        source_working_dir=tmp_path / ".swe" / "source-scope",
        source_id="source-a",
    )

    target_scope_id = encode_scope_id("tenant-b", "source-a")
    assert result.success is True
    assert (
        secret_dir / target_scope_id / "providers" / "active_model.json"
    ).exists()
    assert not (secret_dir / "tenant-b" / "providers").exists()
