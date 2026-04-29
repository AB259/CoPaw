# -*- coding: utf-8 -*-
import json
import pytest
from pathlib import Path


def test_get_marketplace_dir(tmp_path):
    from market.marketplace.fs import get_marketplace_dir

    result = get_marketplace_dir(tmp_path, "source_a")
    assert result == tmp_path / "source_a"


def test_get_index_path(tmp_path):
    from market.marketplace.fs import get_index_path

    result = get_index_path(tmp_path, "source_a")
    assert result == tmp_path / "source_a" / "index.json"


def test_load_index_returns_empty_when_not_exists(tmp_path):
    from market.marketplace.fs import load_index

    result = load_index(tmp_path, "source_a")
    assert result == []


def test_save_and_load_index(tmp_path):
    from market.marketplace.fs import load_index, save_index
    from market.marketplace.models import MarketItem

    item = MarketItem(
        item_id="uuid-1",
        item_type="skill",
        name="test_skill",
        description="desc",
        version="1.0.0",
        creator_id="user1",
        creator_name="User One",
        category_id=None,
        bbk_ids=[],
        status="active",
    )
    save_index(tmp_path, "source_a", [item])
    loaded = load_index(tmp_path, "source_a")
    assert len(loaded) == 1
    assert loaded[0].name == "test_skill"


def test_get_skill_dir_in_marketplace(tmp_path):
    from market.marketplace.fs import get_skill_dir

    result = get_skill_dir(tmp_path, "source_a", "item-123")
    assert result == tmp_path / "source_a" / "skills" / "item-123"


def test_get_user_skills_dir(tmp_path):
    from market.marketplace.fs import get_user_skills_dir

    result = get_user_skills_dir(tmp_path, "user1", "agent1")
    assert result == tmp_path / "user1" / "workspaces" / "agent1" / "skills"
