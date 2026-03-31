# -*- coding: utf-8 -*-
"""Tests for tracing store module.

Tests cover:
- Sanitization functions
- CRUD operations (traces, spans)
- Query operations (sessions, traces, users, overview)
- Both in-memory and database storage modes
- Event type filtering
- Empty results handling
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from copaw.tracing.config import TracingConfig
from copaw.tracing.models import EventType, Trace, TraceStatus, Span
from copaw.tracing.store import TraceStore, sanitize_dict, sanitize_string


class TestSanitizeFunctions:
    """Tests for sanitization functions."""

    def test_sanitize_dict_redacts_sensitive_keys(self):
        """Sensitive keys should be redacted."""
        data = {
            "api_key": "secret123",
            "password": "mypass",
            "Authorization": "Bearer token",
            "normal_field": "visible",
        }
        result = sanitize_dict(data)
        assert result["api_key"] == "[REDACTED]"
        assert result["password"] == "[REDACTED]"
        assert result["Authorization"] == "[REDACTED]"
        assert result["normal_field"] == "visible"

    def test_sanitize_dict_truncates_long_strings(self):
        """Long strings should be truncated."""
        data = {"text": "a" * 1000}
        result = sanitize_dict(data, max_length=100)
        assert len(result["text"]) == 103
        assert result["text"].endswith("...")

    def test_sanitize_dict_handles_nested_dicts(self):
        """Nested dicts should also be sanitized."""
        data = {"nested": {"api_key": "secret", "value": "normal"}}
        result = sanitize_dict(data)
        assert result["nested"]["api_key"] == "[REDACTED]"
        assert result["nested"]["value"] == "normal"

    def test_sanitize_dict_handles_none(self):
        assert sanitize_dict(None) is None

    def test_sanitize_string_truncates(self):
        text = "a" * 1000
        result = sanitize_string(text, max_length=100)
        assert len(result) == 103
        assert result.endswith("...")

    def test_sanitize_string_handles_none(self):
        assert sanitize_string(None) is None


class TestTraceStoreMemory:
    """Tests for TraceStore in-memory mode."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    # CRUD Operations

    def test_create_and_get_trace(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now() - timedelta(minutes=5),
            status=TraceStatus.RUNNING,
        )
        asyncio.run(store.create_trace(trace))
        result = asyncio.run(store.get_trace("trace-001"))
        assert result is not None
        assert result.trace_id == "trace-001"
        assert result.user_id == "user-001"

    def test_update_trace(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.RUNNING,
        )
        asyncio.run(store.create_trace(trace))
        trace.status = TraceStatus.COMPLETED
        trace.duration_ms = 1000
        asyncio.run(store.update_trace(trace))
        result = asyncio.run(store.get_trace("trace-001"))
        assert result.status == TraceStatus.COMPLETED
        assert result.duration_ms == 1000

    def test_create_and_get_spans(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.RUNNING,
        )
        asyncio.run(store.create_trace(trace))
        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_span",
            event_type=EventType.TOOL_CALL_END,
            start_time=datetime.now(),
            user_id="user-001",
            session_id="session-001",
            channel="console",
            tool_name="test_tool",
            duration_ms=100,
        )
        asyncio.run(store.create_span(span))
        spans = asyncio.run(store.get_spans("trace-001"))
        assert len(spans) == 1
        assert spans[0].span_id == "span-001"

    def test_batch_create_spans(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.RUNNING,
        )
        asyncio.run(store.create_trace(trace))
        spans = [
            Span(
                span_id=f"span-{i}",
                trace_id="trace-001",
                name=f"span_{i}",
                event_type=EventType.SKILL_INVOCATION,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                skill_name=f"skill_{i}",
            )
            for i in range(5)
        ]
        asyncio.run(store.batch_create_spans(spans))
        result = asyncio.run(store.get_spans("trace-001"))
        assert len(result) == 5

    # Session Queries

    def test_get_sessions_pagination(self, store):
        for i in range(25):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-001",
                session_id=f"session-{i // 5}",
                channel="console",
                start_time=datetime.now() - timedelta(minutes=i),
                status=TraceStatus.COMPLETED,
                total_input_tokens=100,
                total_output_tokens=50,
            )
            asyncio.run(store.create_trace(trace))

        sessions, total = asyncio.run(store.get_sessions(page=1, page_size=10))
        assert len(sessions) == 5
        assert total == 5

        sessions, total = asyncio.run(store.get_sessions(page=1, page_size=2))
        assert len(sessions) == 2
        assert total == 5

    def test_get_sessions_filters(self, store):
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i % 2}",
                session_id=f"session-{i}",
                channel="console",
                start_time=datetime.now() - timedelta(days=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        sessions, total = asyncio.run(store.get_sessions(user_id="user-0"))
        assert total == 5
        for s in sessions:
            assert s.user_id == "user-0"

        sessions, total = asyncio.run(store.get_sessions(session_id="session-1"))
        assert total >= 1

    def test_get_sessions_date_filter(self, store):
        now = datetime.now()
        for i in range(5):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-001",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        sessions, total = asyncio.run(store.get_sessions(
            start_date=now - timedelta(days=2),
            end_date=now,
        ))
        assert total == 3

    def test_get_session_stats(self, store):
        session_id = "session-001"
        for i in range(3):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-001",
                session_id=session_id,
                channel="console",
                start_time=datetime.now() - timedelta(minutes=i),
                status=TraceStatus.COMPLETED,
                total_input_tokens=100,
                total_output_tokens=50,
                duration_ms=1000 * (i + 1),
                model_name="gpt-4",
            )
            asyncio.run(store.create_trace(trace))

        asyncio.run(store.batch_create_spans([
            Span(
                span_id=f"skill-span-{i}",
                trace_id=f"trace-{i}",
                name=f"skill_{i}",
                event_type=EventType.SKILL_INVOCATION,
                start_time=datetime.now(),
                user_id="user-001",
                session_id=session_id,
                channel="console",
                skill_name=f"skill_{i}",
                duration_ms=100,
            )
            for i in range(3)
        ]))

        stats = asyncio.run(store.get_session_stats(session_id))
        assert stats.session_id == session_id
        assert stats.user_id == "user-001"
        assert stats.total_traces == 3
        assert stats.total_tokens == 450
        assert stats.input_tokens == 300
        assert stats.output_tokens == 150
        assert len(stats.skills_used) == 3

    # Trace Queries

    def test_get_traces_pagination(self, store):
        for i in range(25):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-001",
                session_id="session-001",
                channel="console",
                start_time=datetime.now() - timedelta(minutes=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        traces, total = asyncio.run(store.get_traces(page=1, page_size=10))
        assert len(traces) == 10
        assert total == 25

        traces, total = asyncio.run(store.get_traces(page=2, page_size=10))
        assert len(traces) == 10

        traces, total = asyncio.run(store.get_traces(page=3, page_size=10))
        assert len(traces) == 5

    def test_get_traces_filters(self, store):
        now = datetime.now()
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i % 2}",
                session_id=f"session-{i % 3}",
                channel="console",
                start_time=now - timedelta(hours=i),
                status=TraceStatus.COMPLETED if i % 2 == 0 else TraceStatus.ERROR,
            )
            asyncio.run(store.create_trace(trace))

        traces, total = asyncio.run(store.get_traces(user_id="user-0"))
        assert total == 5

        traces, total = asyncio.run(store.get_traces(session_id="session-0"))
        assert total >= 3

        traces, total = asyncio.run(store.get_traces(status="completed"))
        assert total == 5

        traces, total = asyncio.run(store.get_traces(
            start_date=now - timedelta(hours=3),
            end_date=now,
        ))
        assert total == 4

    def test_get_traces_combined_filters(self, store):
        now = datetime.now()
        for i in range(20):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i % 2}",
                session_id="session-001",
                channel="console",
                start_time=now - timedelta(hours=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        traces, _ = asyncio.run(store.get_traces(
            user_id="user-0",
            start_date=now - timedelta(hours=5),
            end_date=now,
        ))
        for t in traces:
            assert t.user_id == "user-0"

    # User Queries

    def test_get_users_pagination(self, store):
        for i in range(30):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i % 10}",
                session_id=f"session-{i}",
                channel="console",
                start_time=datetime.now() - timedelta(minutes=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        users, total = asyncio.run(store.get_users(page=1, page_size=5))
        assert len(users) == 5
        assert total == 10

    def test_get_users_filter_by_user_id(self, store):
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i}",
                session_id="session-001",
                channel="console",
                start_time=datetime.now(),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        users, total = asyncio.run(store.get_users(user_id="user-1"))
        assert total >= 1

    def test_get_user_stats(self, store):
        user_id = "user-001"
        for i in range(5):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=user_id,
                session_id=f"session-{i}",
                channel="console",
                start_time=datetime.now() - timedelta(days=i),
                status=TraceStatus.COMPLETED,
                total_input_tokens=100,
                total_output_tokens=50,
                duration_ms=1000,
                model_name="gpt-4" if i % 2 == 0 else "gpt-3.5",
            )
            asyncio.run(store.create_trace(trace))

        asyncio.run(store.batch_create_spans([
            Span(
                span_id=f"tool-span-{i}",
                trace_id=f"trace-{i}",
                name="tool_test",
                event_type=EventType.TOOL_CALL_END,
                start_time=datetime.now(),
                user_id=user_id,
                session_id=f"session-{i}",
                channel="console",
                tool_name=f"tool_{i}",
                duration_ms=100,
            )
            for i in range(5)
        ]))

        stats = asyncio.run(store.get_user_stats(user_id))
        assert stats.user_id == user_id
        assert stats.total_sessions == 5
        assert stats.total_tokens == 750
        assert len(stats.tools_used) == 5

    # Overview Stats

    def test_get_overview_stats(self, store):
        now = datetime.now()
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i % 3}",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(hours=i),
                end_time=now - timedelta(hours=i) + timedelta(seconds=30),
                duration_ms=30000,
                status=TraceStatus.COMPLETED,
                total_input_tokens=100,
                total_output_tokens=50,
                model_name="gpt-4",
            )
            asyncio.run(store.create_trace(trace))

        for i in range(5):
            span = Span(
                span_id=f"skill-{i}",
                trace_id=f"trace-{i}",
                name="skill_test",
                event_type=EventType.SKILL_INVOCATION,
                start_time=now - timedelta(hours=i),
                user_id=f"user-{i % 3}",
                session_id=f"session-{i}",
                channel="console",
                skill_name=f"skill_{i}",
                duration_ms=500,
            )
            asyncio.run(store.create_span(span))

        stats = asyncio.run(store.get_overview_stats(
            start_date=now - timedelta(days=1),
            end_date=now,
        ))
        assert stats.total_users == 3
        assert stats.total_sessions == 10
        assert stats.total_tokens == 1500
        assert len(stats.top_skills) == 5

    # Trace Detail

    def test_get_trace_detail(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
            total_input_tokens=100,
            total_output_tokens=50,
        )
        asyncio.run(store.create_trace(trace))

        spans = [
            Span(
                span_id=f"span-{i}",
                trace_id="trace-001",
                name=f"span_{i}",
                event_type=EventType.TOOL_CALL_END if i in [0, 2] else EventType.LLM_INPUT,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                tool_name=f"tool_{i}" if i in [0, 2] else None,
                duration_ms=100,
            )
            for i in range(5)
        ]
        asyncio.run(store.batch_create_spans(spans))

        detail = asyncio.run(store.get_trace_detail("trace-001"))
        assert detail is not None
        assert detail.trace.trace_id == "trace-001"
        assert len(detail.spans) == 5
        assert detail.tool_duration_ms == 200
        assert detail.llm_duration_ms == 300


class TestTraceStoreDatabase:
    """Tests for TraceStore database mode."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.is_connected = True
        db.execute = AsyncMock()
        db.execute_many = AsyncMock()
        db.fetch_one = AsyncMock()
        db.fetch_all = AsyncMock()
        db.close = AsyncMock()
        return db

    @pytest.fixture
    def store(self, mock_db):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=mock_db)
        asyncio.run(store.initialize())
        return store

    def test_db_create_trace(self, store, mock_db):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.RUNNING,
        )
        asyncio.run(store.create_trace(trace))
        mock_db.execute.assert_called_once()

    def test_db_get_traces_pagination(self, store, mock_db):
        mock_db.fetch_one.side_effect = [{"total": 25}]
        mock_db.fetch_all.return_value = [
            {
                "trace_id": f"trace-{i}",
                "user_id": "user-001",
                "session_id": "session-001",
                "channel": "console",
                "start_time": datetime.now(),
                "duration_ms": 1000,
                "total_tokens": 150,
                "model_name": "gpt-4",
                "status": "completed",
                "skills_count": 2,
            }
            for i in range(10)
        ]

        traces, total = asyncio.run(store.get_traces(page=1, page_size=10))
        assert len(traces) == 10
        assert total == 25

    def test_db_get_traces_with_filters(self, store, mock_db):
        mock_db.fetch_one.return_value = {"total": 5}
        mock_db.fetch_all.return_value = []

        asyncio.run(store.get_traces(
            page=1,
            page_size=10,
            user_id="user-001",
            status="completed",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
        ))
        assert mock_db.fetch_one.called
        assert mock_db.fetch_all.called

    def test_db_get_sessions_pagination(self, store, mock_db):
        mock_db.fetch_one.return_value = {"total": 15}
        mock_db.fetch_all.return_value = [
            {
                "session_id": f"session-{i}",
                "user_id": "user-001",
                "channel": "console",
                "total_traces": 5,
                "total_tokens": 1000,
                "total_skills": 3,
                "first_active": datetime.now(),
                "last_active": datetime.now(),
            }
            for i in range(10)
        ]

        sessions, total = asyncio.run(store.get_sessions(page=1, page_size=10))
        assert len(sessions) == 10
        assert total == 15

    def test_db_get_sessions_with_filters(self, store, mock_db):
        mock_db.fetch_one.return_value = {"total": 3}
        mock_db.fetch_all.return_value = []

        asyncio.run(store.get_sessions(
            page=1,
            page_size=10,
            user_id="user-001",
            session_id="session-1",
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
        ))
        assert mock_db.fetch_one.called
        assert mock_db.fetch_all.called

    def test_db_get_session_stats(self, store, mock_db):
        mock_db.fetch_one.return_value = {
            "user_id": "user-001",
            "channel": "console",
            "total_traces": 5,
            "input_tokens": 500,
            "output_tokens": 250,
            "total_tokens": 750,
            "avg_duration": 1000.0,
            "first_active": datetime.now(),
            "last_active": datetime.now(),
        }
        mock_db.fetch_all.return_value = []

        stats = asyncio.run(store.get_session_stats("session-001"))
        assert stats.session_id == "session-001"
        assert stats.user_id == "user-001"
        assert stats.total_traces == 5

    def test_db_get_users_pagination(self, store, mock_db):
        mock_db.fetch_one.return_value = {"total": 20}
        mock_db.fetch_all.return_value = [
            {
                "user_id": f"user-{i}",
                "total_sessions": 5,
                "total_conversations": 3,
                "total_tokens": 1000,
                "total_skills": 2,
                "last_active": datetime.now(),
            }
            for i in range(10)
        ]

        users, total = asyncio.run(store.get_users(page=1, page_size=10))
        assert len(users) == 10
        assert total == 20


class TestEventTypeFiltering:
    """Tests for proper event_type filtering."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_tools_counted_only_from_tool_call_end(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
        )
        asyncio.run(store.create_trace(trace))

        start_span = Span(
            span_id="span-start",
            trace_id="trace-001",
            name="tool_test",
            event_type=EventType.TOOL_CALL_START,
            start_time=datetime.now(),
            user_id="user-001",
            session_id="session-001",
            channel="console",
            tool_name="test_tool",
            duration_ms=50,
        )
        asyncio.run(store.create_span(start_span))

        end_span = Span(
            span_id="span-end",
            trace_id="trace-001",
            name="tool_test",
            event_type=EventType.TOOL_CALL_END,
            start_time=datetime.now(),
            user_id="user-001",
            session_id="session-001",
            channel="console",
            tool_name="test_tool",
            duration_ms=100,
        )
        asyncio.run(store.create_span(end_span))

        stats = asyncio.run(store.get_overview_stats())
        assert len(stats.top_tools) == 1
        assert stats.top_tools[0].count == 1

    def test_skills_counted_from_skill_invocation(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
            skills_used=["skill_1", "skill_2"],
        )
        asyncio.run(store.create_trace(trace))

        for i in range(3):
            span = Span(
                span_id=f"skill-span-{i}",
                trace_id="trace-001",
                name=f"skill_{i}",
                event_type=EventType.SKILL_INVOCATION,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                skill_name=f"skill_{i}",
                duration_ms=100,
            )
            asyncio.run(store.create_span(span))

        stats = asyncio.run(store.get_overview_stats())
        assert len(stats.top_skills) == 3

    def test_mixed_events_separated_correctly(self, store):
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
        )
        asyncio.run(store.create_trace(trace))

        spans = [
            Span(
                span_id="tool-1",
                trace_id="trace-001",
                name="tool_span",
                event_type=EventType.TOOL_CALL_END,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                tool_name="tool_1",
                duration_ms=100,
            ),
            Span(
                span_id="skill-1",
                trace_id="trace-001",
                name="skill_span",
                event_type=EventType.SKILL_INVOCATION,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                skill_name="skill_1",
                duration_ms=200,
            ),
            Span(
                span_id="llm-1",
                trace_id="trace-001",
                name="llm_span",
                event_type=EventType.LLM_INPUT,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                duration_ms=300,
            ),
        ]
        asyncio.run(store.batch_create_spans(spans))

        stats = asyncio.run(store.get_overview_stats())
        assert len(stats.top_tools) == 1
        assert len(stats.top_skills) == 1
        assert stats.top_tools[0].tool_name == "tool_1"
        assert stats.top_skills[0].skill_name == "skill_1"


class TestEmptyResults:
    """Tests for handling empty results."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_empty_sessions_list(self, store):
        sessions, total = asyncio.run(store.get_sessions())
        assert sessions == []
        assert total == 0

    def test_empty_traces_list(self, store):
        traces, total = asyncio.run(store.get_traces())
        assert traces == []
        assert total == 0

    def test_empty_users_list(self, store):
        users, total = asyncio.run(store.get_users())
        assert users == []
        assert total == 0

    def test_empty_overview_stats(self, store):
        stats = asyncio.run(store.get_overview_stats())
        assert stats.total_users == 0
        assert stats.total_sessions == 0
        assert stats.total_tokens == 0
        assert stats.top_tools == []
        assert stats.top_skills == []
        assert stats.top_mcp_tools == []
        assert stats.mcp_servers == []

    def test_empty_session_stats(self, store):
        stats = asyncio.run(store.get_session_stats("non-existent"))
        assert stats.session_id == "non-existent"
        assert stats.user_id == ""
        assert stats.total_traces == 0

    def test_empty_user_stats(self, store):
        stats = asyncio.run(store.get_user_stats("non-existent"))
        assert stats.user_id == "non-existent"
        assert stats.total_sessions == 0

    def test_empty_trace_detail(self, store):
        detail = asyncio.run(store.get_trace_detail("non-existent"))
        assert detail is None


class TestMCPToolStatistics:
    """Tests for MCP tool usage statistics."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_mcp_tools_separated_from_regular_tools(self, store):
        """MCP tools should be tracked separately from regular tools."""
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
        )
        asyncio.run(store.create_trace(trace))

        # Regular tool
        regular_span = Span(
            span_id="span-regular",
            trace_id="trace-001",
            name="regular_tool",
            event_type=EventType.TOOL_CALL_END,
            start_time=datetime.now(),
            user_id="user-001",
            session_id="session-001",
            channel="console",
            tool_name="regular_tool",
            duration_ms=100,
            mcp_server=None,  # Not from MCP
        )
        asyncio.run(store.create_span(regular_span))

        # MCP tool
        mcp_span = Span(
            span_id="span-mcp",
            trace_id="trace-001",
            name="mcp_tool",
            event_type=EventType.TOOL_CALL_END,
            start_time=datetime.now(),
            user_id="user-001",
            session_id="session-001",
            channel="console",
            tool_name="filesystem_read",
            duration_ms=200,
            mcp_server="filesystem",  # From MCP
        )
        asyncio.run(store.create_span(mcp_span))

        stats = asyncio.run(store.get_overview_stats())

        # Regular tool in top_tools, not in MCP tools
        assert len(stats.top_tools) == 1
        assert stats.top_tools[0].tool_name == "regular_tool"

        # MCP tool in top_mcp_tools
        assert len(stats.top_mcp_tools) == 1
        assert stats.top_mcp_tools[0].tool_name == "filesystem_read"
        assert stats.top_mcp_tools[0].mcp_server == "filesystem"

    def test_mcp_server_grouping(self, store):
        """MCP tools should be grouped by server."""
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
        )
        asyncio.run(store.create_trace(trace))

        # Create tools from two MCP servers
        spans = [
            Span(
                span_id=f"span-{i}",
                trace_id="trace-001",
                name=f"tool_{i}",
                event_type=EventType.TOOL_CALL_END,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                tool_name=f"tool_{i}",
                duration_ms=100 * (i + 1),
                mcp_server="server_a" if i < 2 else "server_b",
            )
            for i in range(4)
        ]
        asyncio.run(store.batch_create_spans(spans))

        stats = asyncio.run(store.get_overview_stats())

        # Should have 2 servers
        assert len(stats.mcp_servers) == 2

        # Server A has 2 tools, Server B has 2 tools
        server_names = {s.server_name for s in stats.mcp_servers}
        assert server_names == {"server_a", "server_b"}

        for server in stats.mcp_servers:
            assert server.tool_count == 2
            assert server.total_calls == 2

    def test_mcp_tools_with_errors(self, store):
        """MCP tools should track error counts."""
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id="session-001",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
        )
        asyncio.run(store.create_trace(trace))

        # Create successful and failed MCP tool calls
        for i in range(3):
            span = Span(
                span_id=f"span-{i}",
                trace_id="trace-001",
                name=f"tool_{i}",
                event_type=EventType.TOOL_CALL_END,
                start_time=datetime.now(),
                user_id="user-001",
                session_id="session-001",
                channel="console",
                tool_name="mcp_tool",
                duration_ms=100,
                mcp_server="test_server",
                error="Failed" if i == 2 else None,
            )
            asyncio.run(store.create_span(span))

        stats = asyncio.run(store.get_overview_stats())

        assert len(stats.top_mcp_tools) == 1
        assert stats.top_mcp_tools[0].count == 3
        assert stats.top_mcp_tools[0].error_count == 1

        assert len(stats.mcp_servers) == 1
        assert stats.mcp_servers[0].error_count == 1

    def test_session_stats_mcp_tools(self, store):
        """Session stats should include MCP tools used in the session."""
        session_id = "session-001"
        trace = Trace(
            trace_id="trace-001",
            user_id="user-001",
            session_id=session_id,
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
        )
        asyncio.run(store.create_trace(trace))

        # Regular tool
        regular_span = Span(
            span_id="span-regular",
            trace_id="trace-001",
            name="regular_tool",
            event_type=EventType.TOOL_CALL_END,
            start_time=datetime.now(),
            user_id="user-001",
            session_id=session_id,
            channel="console",
            tool_name="regular_tool",
            duration_ms=100,
            mcp_server=None,
        )
        asyncio.run(store.create_span(regular_span))

        # MCP tools from different servers
        mcp_spans = [
            Span(
                span_id=f"span-mcp-{i}",
                trace_id="trace-001",
                name=f"mcp_tool_{i}",
                event_type=EventType.TOOL_CALL_END,
                start_time=datetime.now(),
                user_id="user-001",
                session_id=session_id,
                channel="console",
                tool_name=f"mcp_tool_{i}",
                duration_ms=100,
                mcp_server="filesystem" if i < 2 else "database",
            )
            for i in range(3)
        ]
        asyncio.run(store.batch_create_spans(mcp_spans))

        stats = asyncio.run(store.get_session_stats(session_id))

        # Should have MCP tools
        assert len(stats.mcp_tools_used) == 3

        # MCP tools should have mcp_server set
        for tool in stats.mcp_tools_used:
            assert tool.mcp_server in ["filesystem", "database"]

        # Regular tools should NOT be in mcp_tools_used
        regular_tool_names = [t.tool_name for t in stats.tools_used]
        mcp_tool_names = [t.tool_name for t in stats.mcp_tools_used]
        assert "regular_tool" in regular_tool_names
        assert "regular_tool" not in mcp_tool_names


class TestMCPToolStatisticsDatabase:
    """Tests for MCP tool usage statistics in database mode."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.is_connected = True
        db.execute = AsyncMock()
        db.execute_many = AsyncMock()
        db.fetch_one = AsyncMock()
        db.fetch_all = AsyncMock()
        db.close = AsyncMock()
        return db

    @pytest.fixture
    def store(self, mock_db):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=mock_db)
        asyncio.run(store.initialize())
        return store

    def test_db_get_overview_mcp_tools(self, store, mock_db):
        """Database mode should query MCP tools correctly."""
        mock_db.fetch_one.return_value = {
            "online_users": 5,
            "total_users": 10,
            "total_sessions": 20,
            "total_conversations": 50,
            "total_tokens": 10000,
            "input_tokens": 6000,
            "output_tokens": 4000,
            "avg_duration": 1500.0,
        }
        mock_db.fetch_all.return_value = []

        stats = asyncio.run(store.get_overview_stats())
        assert mock_db.fetch_one.called
        assert mock_db.fetch_all.called

    def test_db_get_session_stats_with_mcp_tools(self, store, mock_db):
        """Database mode should return MCP tools in session stats."""
        mock_db.fetch_one.return_value = {
            "user_id": "user-001",
            "channel": "console",
            "total_traces": 5,
            "input_tokens": 500,
            "output_tokens": 250,
            "total_tokens": 750,
            "avg_duration": 1000.0,
            "first_active": datetime.now(),
            "last_active": datetime.now(),
        }

        # Mock MCP tools query result
        mock_db.fetch_all.side_effect = [
            [],  # model_usage
            [],  # tools_used (non-MCP)
            [],  # skills_used
            [
                {
                    "tool_name": "read_file",
                    "mcp_server": "filesystem",
                    "count": 3,
                    "avg_duration": 100.0,
                    "error_count": 0,
                },
                {
                    "tool_name": "query_db",
                    "mcp_server": "database",
                    "count": 2,
                    "avg_duration": 200.0,
                    "error_count": 1,
                },
            ],  # mcp_tools_used
        ]

        stats = asyncio.run(store.get_session_stats("session-001"))

        assert stats.session_id == "session-001"
        assert len(stats.mcp_tools_used) == 2
        assert stats.mcp_tools_used[0].tool_name == "read_file"
        assert stats.mcp_tools_used[0].mcp_server == "filesystem"
        assert stats.mcp_tools_used[1].tool_name == "query_db"
        assert stats.mcp_tools_used[1].mcp_server == "database"

    def test_db_session_tools_excludes_mcp(self, store, mock_db):
        """Database mode should exclude MCP tools from regular tools query."""
        mock_db.fetch_one.return_value = {
            "user_id": "user-001",
            "channel": "console",
            "total_traces": 5,
            "input_tokens": 500,
            "output_tokens": 250,
            "total_tokens": 750,
            "avg_duration": 1000.0,
            "first_active": datetime.now(),
            "last_active": datetime.now(),
        }

        # Regular tools (non-MCP) should have mcp_server IS NULL
        mock_db.fetch_all.side_effect = [
            [],  # model_usage
            [
                {
                    "tool_name": "regular_tool",
                    "count": 5,
                    "avg_duration": 50.0,
                    "error_count": 0,
                }
            ],  # tools_used (non-MCP only)
            [],  # skills_used
            [],  # mcp_tools_used
        ]

        stats = asyncio.run(store.get_session_stats("session-001"))

        # Only regular tool in tools_used
        assert len(stats.tools_used) == 1
        assert stats.tools_used[0].tool_name == "regular_tool"

        # No MCP tools
        assert len(stats.mcp_tools_used) == 0

    def test_db_overview_mcp_servers_grouped(self, store, mock_db):
        """Database mode should group MCP tools by server in overview."""
        mock_db.fetch_one.return_value = {
            "online_users": 5,
            "total_users": 10,
            "total_sessions": 20,
            "total_conversations": 50,
            "total_tokens": 10000,
            "input_tokens": 6000,
            "output_tokens": 4000,
            "avg_duration": 1500.0,
        }

        # MCP tools with server info
        mock_db.fetch_all.side_effect = [
            [],  # model_distribution
            [],  # top_tools (non-MCP)
            [],  # top_skills
            [
                {
                    "tool_name": "read",
                    "mcp_server": "filesystem",
                    "count": 10,
                    "avg_duration": 50.0,
                    "error_count": 0,
                },
                {
                    "tool_name": "write",
                    "mcp_server": "filesystem",
                    "count": 5,
                    "avg_duration": 100.0,
                    "error_count": 1,
                },
                {
                    "tool_name": "query",
                    "mcp_server": "database",
                    "count": 8,
                    "avg_duration": 200.0,
                    "error_count": 0,
                },
            ],  # top_mcp_tools
            [
                # mcp_servers query
                {
                    "mcp_server": "filesystem",
                    "tool_count": 2,
                    "total_calls": 15,
                    "avg_duration": 66.67,
                    "error_count": 1,
                },
                {
                    "mcp_server": "database",
                    "tool_count": 1,
                    "total_calls": 8,
                    "avg_duration": 200.0,
                    "error_count": 0,
                },
            ],
            # tools for each server (2 servers, each needs a fetch_all)
            [
                {
                    "tool_name": "read",
                    "mcp_server": "filesystem",
                    "count": 10,
                    "avg_duration": 50.0,
                    "error_count": 0,
                },
                {
                    "tool_name": "write",
                    "mcp_server": "filesystem",
                    "count": 5,
                    "avg_duration": 100.0,
                    "error_count": 1,
                },
            ],
            [
                {
                    "tool_name": "query",
                    "mcp_server": "database",
                    "count": 8,
                    "avg_duration": 200.0,
                    "error_count": 0,
                },
            ],
        ]

        stats = asyncio.run(store.get_overview_stats())

        # Should have MCP tools
        assert len(stats.top_mcp_tools) == 3

        # Should have 2 servers grouped
        assert len(stats.mcp_servers) == 2
        server_names = {s.server_name for s in stats.mcp_servers}
        assert server_names == {"filesystem", "database"}

        # Filesystem server: 2 tools, 15 total calls, 1 error
        fs_server = next(s for s in stats.mcp_servers if s.server_name == "filesystem")
        assert fs_server.tool_count == 2
        assert fs_server.total_calls == 15
        assert fs_server.error_count == 1
