# -*- coding: utf-8 -*-
"""Tests for workload-specific LLM runtime config fields."""

from swe.config.config import AgentsRunningConfig


def test_workload_specific_llm_config_fields_are_optional() -> None:
    config = AgentsRunningConfig()

    assert config.llm_chat_max_concurrent is None
    assert config.llm_cron_max_concurrent is None
    assert config.llm_chat_acquire_timeout is None
    assert config.llm_cron_acquire_timeout is None


def test_workload_specific_llm_config_fields_accept_overrides() -> None:
    config = AgentsRunningConfig(
        llm_chat_max_concurrent=4,
        llm_cron_max_concurrent=2,
        llm_chat_acquire_timeout=20.0,
        llm_cron_acquire_timeout=120.0,
    )

    assert config.llm_chat_max_concurrent == 4
    assert config.llm_cron_max_concurrent == 2
    assert config.llm_chat_acquire_timeout == 20.0
    assert config.llm_cron_acquire_timeout == 120.0
