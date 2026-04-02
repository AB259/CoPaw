# -*- coding: utf-8 -*-
"""Unit tests for tenant-scoped bootstrap helper functions."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from copaw.agents.skills_manager import ensure_skill_pool_initialized
from copaw.app.migration import ensure_default_agent_exists, ensure_qa_agent_exists


def test_ensure_default_agent_exists_uses_tenant_working_dir(tmp_path):
    tenant_dir = tmp_path / "tenant-alpha"

    ensure_default_agent_exists(working_dir=tenant_dir)

    config_path = tenant_dir / "config.json"
    default_workspace = tenant_dir / "workspaces" / "default"

    assert config_path.exists()
    assert default_workspace.exists()
    assert (default_workspace / "chats.json").exists()
    assert (default_workspace / "jobs.json").exists()

    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    profiles = config_data.get("agents", {}).get("profiles", {})
    default_profile = profiles.get("default") or {}
    assert default_profile.get("workspace_dir") == str(default_workspace)


def test_ensure_qa_agent_exists_uses_tenant_working_dir(tmp_path):
    tenant_dir = tmp_path / "tenant-bravo"

    ensure_qa_agent_exists(working_dir=tenant_dir)

    config_path = tenant_dir / "config.json"
    qa_workspace = tenant_dir / "workspaces" / "qa"

    assert config_path.exists()
    assert qa_workspace.exists()
    assert (qa_workspace / "chats.json").exists()
    assert (qa_workspace / "jobs.json").exists()

    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    profiles = config_data.get("agents", {}).get("profiles", {})
    qa_profile = profiles.get("qa") or {}
    assert qa_profile.get("workspace_dir") == str(qa_workspace)


def test_ensure_skill_pool_initialized_uses_tenant_working_dir(tmp_path):
    tenant_dir = tmp_path / "tenant-charlie"

    created = ensure_skill_pool_initialized(working_dir=tenant_dir)

    assert (tenant_dir / "skill_pool").is_dir()
    assert created in (True, False)
