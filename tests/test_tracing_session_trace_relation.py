# -*- coding: utf-8 -*-
"""Tests for session-trace hierarchical relationship.

These tests verify the complete hierarchy: User -> Session -> Trace -> Span
"""
import asyncio
from datetime import datetime, timedelta

import pytest

from copaw.tracing.config import TracingConfig
from copaw.tracing.models import EventType, Trace, TraceStatus, Span
from copaw.tracing.store import TraceStore


class TestSessionTraceHierarchy:
    """Tests for session-trace hierarchical queries."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    @pytest.fixture
    def populated_store(self, store):
        """Create store with hierarchical test data:
        - 3 users (user-1, user-2, user-3)
        - 5 sessions (user-1: 2, user-2: 2, user-3: 1)
        - 15 traces (3 per session)
        - Multiple spans per trace
        """
        now = datetime.now()

        for session_idx in range(5):
            user_id = f"user-{session_idx // 2 + 1}"
            session_id = f"session-{session_idx}"

            for trace_idx in range(3):
                trace_num = session_idx * 3 + trace_idx
                trace = Trace(
                    trace_id=f"trace-{trace_num}",
                    user_id=user_id,
                    session_id=session_id,
                    channel="console",
                    start_time=now - timedelta(minutes=trace_num),
                    status=TraceStatus.COMPLETED,
                    total_input_tokens=100 + trace_idx * 10,
                    total_output_tokens=50 + trace_idx * 5,
                    duration_ms=1000 * (trace_idx + 1),
                    model_name="gpt-4" if trace_idx % 2 == 0 else "gpt-3.5",
                )
                asyncio.run(store.create_trace(trace))

                spans = [
                    Span(
                        span_id=f"span-{trace_num}-{span_idx}",
                        trace_id=f"trace-{trace_num}",
                        name=f"span_{span_idx}",
                        event_type=EventType.TOOL_CALL_END if span_idx == 0 else EventType.SKILL_INVOCATION,
                        start_time=now - timedelta(minutes=trace_num, seconds=span_idx),
                        user_id=user_id,
                        session_id=session_id,
                        channel="console",
                        tool_name=f"tool_{span_idx}" if span_idx == 0 else None,
                        skill_name=f"skill_{span_idx}" if span_idx > 0 else None,
                        duration_ms=100 * (span_idx + 1),
                    )
                    for span_idx in range(3)
                ]
                asyncio.run(store.batch_create_spans(spans))

        return store

    def test_session_list_shows_trace_counts(self, populated_store):
        sessions, total = asyncio.run(populated_store.get_sessions())
        assert total == 5
        for session in sessions:
            assert session.total_traces == 3

    def test_session_list_filter_by_user(self, populated_store):
        sessions, total = asyncio.run(populated_store.get_sessions(user_id="user-1"))
        assert total == 2
        for session in sessions:
            assert session.user_id == "user-1"

    def test_session_stats_aggregates_traces(self, populated_store):
        stats = asyncio.run(populated_store.get_session_stats("session-0"))
        assert stats.session_id == "session-0"
        assert stats.user_id == "user-1"
        assert stats.total_traces == 3
        assert stats.input_tokens == 330
        assert stats.output_tokens == 165
        assert stats.total_tokens == 495

    def test_session_stats_shows_model_distribution(self, populated_store):
        stats = asyncio.run(populated_store.get_session_stats("session-0"))
        assert len(stats.model_usage) == 2
        model_names = {m.model_name for m in stats.model_usage}
        assert "gpt-4" in model_names
        assert "gpt-3.5" in model_names

    def test_traces_filtered_by_session(self, populated_store):
        traces, total = asyncio.run(populated_store.get_traces(session_id="session-0"))
        assert total == 3
        for trace in traces:
            assert trace.session_id == "session-0"

    def test_traces_pagination_within_session(self, populated_store):
        traces_page1, total = asyncio.run(
            populated_store.get_traces(session_id="session-0", page=1, page_size=2)
        )
        assert len(traces_page1) == 2
        assert total == 3

        traces_page2, total = asyncio.run(
            populated_store.get_traces(session_id="session-0", page=2, page_size=2)
        )
        assert len(traces_page2) == 1
        assert total == 3

        all_traces = traces_page1 + traces_page2
        for trace in all_traces:
            assert trace.session_id == "session-0"

    def test_trace_detail_includes_spans(self, populated_store):
        detail = asyncio.run(populated_store.get_trace_detail("trace-0"))
        assert detail is not None
        assert detail.trace.trace_id == "trace-0"
        assert len(detail.spans) == 3

    def test_trace_detail_calculates_durations(self, populated_store):
        detail = asyncio.run(populated_store.get_trace_detail("trace-0"))
        assert detail is not None
        assert detail.tool_duration_ms == 100
        assert detail.llm_duration_ms == 0

    def test_complete_hierarchy_query(self, populated_store):
        # Step 1: Get sessions list
        sessions, _ = asyncio.run(populated_store.get_sessions())
        assert len(sessions) == 5

        # Step 2: Select a session and get stats
        selected_session = sessions[0]
        session_stats = asyncio.run(
            populated_store.get_session_stats(selected_session.session_id)
        )
        assert session_stats.total_traces == 3

        # Step 3: Get traces for the selected session
        traces, _ = asyncio.run(
            populated_store.get_traces(session_id=selected_session.session_id)
        )
        assert len(traces) == 3

        # Step 4: Get detail for a specific trace
        selected_trace = traces[0]
        trace_detail = asyncio.run(
            populated_store.get_trace_detail(selected_trace.trace_id)
        )
        assert trace_detail is not None
        assert len(trace_detail.spans) == 3

        # Verify hierarchy consistency
        assert trace_detail.trace.session_id == selected_session.session_id
        assert trace_detail.trace.user_id == session_stats.user_id

    def test_session_with_no_traces(self, store):
        trace = Trace(
            trace_id="trace-orphan",
            user_id="user-1",
            session_id="session-empty",
            channel="console",
            start_time=datetime.now(),
            status=TraceStatus.COMPLETED,
        )
        asyncio.run(store.create_trace(trace))

        stats = asyncio.run(store.get_session_stats("session-empty"))
        assert stats.total_traces == 1

        stats_empty = asyncio.run(store.get_session_stats("session-nonexistent"))
        assert stats_empty.total_traces == 0
        assert stats_empty.user_id == ""

    def test_session_date_filter(self, populated_store):
        now = datetime.now()
        sessions, total = asyncio.run(
            populated_store.get_sessions(
                start_date=now - timedelta(hours=1),
                end_date=now + timedelta(minutes=5),
            )
        )
        assert total == 5

    def test_user_session_trace_relationship(self, populated_store):
        traces, _ = asyncio.run(populated_store.get_traces(user_id="user-1"))
        session_ids = {t.session_id for t in traces}
        assert session_ids == {"session-0", "session-1"}
        assert len(traces) == 6

    def test_skills_counted_in_session_stats(self, populated_store):
        stats = asyncio.run(populated_store.get_session_stats("session-0"))
        assert len(stats.skills_used) == 2

    def test_tools_counted_in_session_stats(self, populated_store):
        stats = asyncio.run(populated_store.get_session_stats("session-0"))
        assert len(stats.tools_used) == 1


class TestSessionStatsCalculation:
    """Tests for session statistics calculation accuracy."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_avg_duration_calculation(self, store):
        session_id = "session-test"
        durations = [1000, 2000, 3000]
        for i, duration in enumerate(durations):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-1",
                session_id=session_id,
                channel="console",
                start_time=datetime.now() - timedelta(minutes=i),
                end_time=datetime.now() - timedelta(minutes=i) + timedelta(milliseconds=duration),
                duration_ms=duration,
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        stats = asyncio.run(store.get_session_stats(session_id))
        assert stats.avg_duration_ms == 2000

    def test_token_aggregation(self, store):
        session_id = "session-test"
        token_data = [(100, 50), (200, 100), (300, 150)]
        for i, (inp, out) in enumerate(token_data):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-1",
                session_id=session_id,
                channel="console",
                start_time=datetime.now() - timedelta(minutes=i),
                status=TraceStatus.COMPLETED,
                total_input_tokens=inp,
                total_output_tokens=out,
            )
            asyncio.run(store.create_trace(trace))

        stats = asyncio.run(store.get_session_stats(session_id))
        assert stats.input_tokens == 600
        assert stats.output_tokens == 300
        assert stats.total_tokens == 900

    def test_first_last_active_times(self, store):
        session_id = "session-test"
        base_time = datetime(2026, 1, 1, 12, 0, 0)

        for i in range(3):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-1",
                session_id=session_id,
                channel="console",
                start_time=base_time + timedelta(hours=i),
                status=TraceStatus.COMPLETED,
                total_input_tokens=100,
                total_output_tokens=50,
            )
            asyncio.run(store.create_trace(trace))

        stats = asyncio.run(store.get_session_stats(
            session_id,
            start_date=base_time - timedelta(days=1),
            end_date=base_time + timedelta(days=1),
        ))
        assert stats.first_active == base_time
        assert stats.last_active == base_time + timedelta(hours=2)


class TestTraceListOrdering:
    """Tests for trace list ordering within sessions."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_traces_ordered_by_start_time_desc(self, store):
        session_id = "session-test"
        base_time = datetime.now()

        for i in [2, 0, 1]:
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-1",
                session_id=session_id,
                channel="console",
                start_time=base_time + timedelta(minutes=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        traces, _ = asyncio.run(store.get_traces(session_id=session_id))
        assert traces[0].trace_id == "trace-2"
        assert traces[1].trace_id == "trace-1"
        assert traces[2].trace_id == "trace-0"

    def test_sessions_ordered_by_last_active_desc(self, store):
        base_time = datetime.now()

        for i in [1, 3, 2]:
            trace = Trace(
                trace_id=f"trace-session-{i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}",
                channel="console",
                start_time=base_time + timedelta(hours=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        sessions, _ = asyncio.run(store.get_sessions())
        assert sessions[0].session_id == "session-3"
        assert sessions[1].session_id == "session-2"
        assert sessions[2].session_id == "session-1"
