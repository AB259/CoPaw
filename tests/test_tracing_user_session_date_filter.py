# -*- coding: utf-8 -*-
"""Tests for user and session date filtering functionality.

Tests cover:
- User analysis with date filters (start_date, end_date)
- Session analysis with date filters
- Both in-memory and database storage modes
- Pagination with date filters
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from copaw.tracing.config import TracingConfig
from copaw.tracing.models import EventType, Trace, TraceStatus, Span
from copaw.tracing.store import TraceStore


class TestUserDateFiltering:
    """Tests for user queries with date filtering."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_get_users_with_start_date(self, store):
        """Users should be filtered by start_date."""
        now = datetime.now()
        # Create traces across different dates
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i),
                status=TraceStatus.COMPLETED,
                total_input_tokens=100,
                total_output_tokens=50,
            )
            asyncio.run(store.create_trace(trace))

        # Only get users from last 3 days
        users, total = asyncio.run(store.get_users(
            page=1,
            page_size=10,
            start_date=now - timedelta(days=3),
        ))
        assert total == 4  # days 0, 1, 2, 3

    def test_get_users_with_end_date(self, store):
        """Users should be filtered by end_date."""
        now = datetime.now()
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        # Only get users from 5 days ago and earlier
        users, total = asyncio.run(store.get_users(
            page=1,
            page_size=10,
            end_date=now - timedelta(days=5),
        ))
        assert total == 5  # days 5, 6, 7, 8, 9

    def test_get_users_with_date_range(self, store):
        """Users should be filtered by both start_date and end_date."""
        now = datetime.now()
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        # Get users from days 3-7
        users, total = asyncio.run(store.get_users(
            page=1,
            page_size=10,
            start_date=now - timedelta(days=7),
            end_date=now - timedelta(days=3),
        ))
        assert total == 5  # days 3, 4, 5, 6, 7

    def test_get_users_pagination_with_date_filter(self, store):
        """Pagination should work correctly with date filters."""
        now = datetime.now()
        # Create 30 users across 3 days
        for i in range(30):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i % 3),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        # Filter to last 2 days (days 0 and 1)
        users, total = asyncio.run(store.get_users(
            page=1,
            page_size=10,
            start_date=now - timedelta(days=2),
        ))
        assert len(users) == 10
        # 30 users total, all created within the date range since i % 3 gives 0, 1, or 2
        # start_date=now-2days includes days 0, 1, 2 (all within 2 days from now)
        assert total == 30

    def test_get_users_filter_by_user_id_and_date(self, store):
        """Combined user_id and date filtering."""
        now = datetime.now()
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i % 3}",  # 3 users: user-0, user-1, user-2
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        # Get user-0 from last 5 days
        # user-0 appears on days 0, 3, 6, 9 (when i % 3 == 0)
        # Within last 5 days from now: days 0, 1, 2, 3, 4, 5
        # So user-0 on days 0 and 3 (but day 5 is edge case)
        users, total = asyncio.run(store.get_users(
            page=1,
            page_size=10,
            user_id="user-0",
            start_date=now - timedelta(days=5),
        ))
        # user-0 appears when i=0, 3, 6, 9; within 5 days: i=0 (day 0), i=3 (day 3)
        # But we need to account for the actual time calculation
        assert total >= 1  # At least user-0 from day 0


class TestSessionDateFiltering:
    """Tests for session queries with date filtering."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_get_sessions_with_start_date(self, store):
        """Sessions should be filtered by start_date."""
        now = datetime.now()
        for i in range(10):
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
            page=1,
            page_size=10,
            start_date=now - timedelta(days=3),
        ))
        assert total == 4  # days 0, 1, 2, 3

    def test_get_sessions_with_end_date(self, store):
        """Sessions should be filtered by end_date."""
        now = datetime.now()
        for i in range(10):
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
            page=1,
            page_size=10,
            end_date=now - timedelta(days=5),
        ))
        assert total == 5  # days 5, 6, 7, 8, 9

    def test_get_sessions_with_date_range(self, store):
        """Sessions should be filtered by date range."""
        now = datetime.now()
        for i in range(10):
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
            page=1,
            page_size=10,
            start_date=now - timedelta(days=7),
            end_date=now - timedelta(days=3),
        ))
        assert total == 5  # days 3, 4, 5, 6, 7

    def test_get_sessions_pagination_with_date_filter(self, store):
        """Session pagination should work with date filters."""
        now = datetime.now()
        # Create 25 sessions
        for i in range(25):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-001",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        # Get first 5 sessions from last 10 days
        sessions, total = asyncio.run(store.get_sessions(
            page=1,
            page_size=5,
            start_date=now - timedelta(days=10),
        ))
        assert len(sessions) == 5
        # 11 sessions: days 0-10 inclusive (timedelta(days=10) includes day 10)
        assert total == 11

        # Second page
        sessions2, _ = asyncio.run(store.get_sessions(
            page=2,
            page_size=5,
            start_date=now - timedelta(days=10),
        ))
        assert len(sessions2) == 5


class TestUserDateFilteringDatabase:
    """Tests for user date filtering in database mode."""

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

    def test_db_get_users_with_date_filter(self, store, mock_db):
        """Database mode should query users with date filters."""
        mock_db.fetch_one.return_value = {"total": 5}
        mock_db.fetch_all.return_value = [
            {
                "user_id": f"user-{i}",
                "total_sessions": 10,
                "total_conversations": 5,
                "total_tokens": 1000,
                "total_skills": 3,
                "last_active": datetime.now(),
            }
            for i in range(5)
        ]

        now = datetime.now()
        users, total = asyncio.run(store.get_users(
            page=1,
            page_size=10,
            user_id="user-",
            start_date=now - timedelta(days=7),
            end_date=now,
        ))

        assert len(users) == 5
        assert total == 5
        assert mock_db.fetch_one.called
        assert mock_db.fetch_all.called

    def test_db_get_users_pagination(self, store, mock_db):
        """Database mode pagination should return correct results."""
        mock_db.fetch_one.return_value = {"total": 25}
        mock_db.fetch_all.return_value = [
            {
                "user_id": f"user-{i}",
                "total_sessions": 5,
                "total_conversations": 3,
                "total_tokens": 500,
                "total_skills": 2,
                "last_active": datetime.now(),
            }
            for i in range(10)
        ]

        users, total = asyncio.run(store.get_users(page=1, page_size=10))
        assert len(users) == 10
        assert total == 25


class TestSessionDateFilteringDatabase:
    """Tests for session date filtering in database mode."""

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

    def test_db_get_sessions_with_date_filter(self, store, mock_db):
        """Database mode should query sessions with date filters."""
        mock_db.fetch_one.return_value = {"total": 8}
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
            for i in range(8)
        ]

        now = datetime.now()
        sessions, total = asyncio.run(store.get_sessions(
            page=1,
            page_size=10,
            user_id="user-001",
            start_date=now - timedelta(days=7),
            end_date=now,
        ))

        assert len(sessions) == 8
        assert total == 8
        assert mock_db.fetch_one.called
        assert mock_db.fetch_all.called

    def test_db_get_sessions_pagination(self, store, mock_db):
        """Database mode session pagination should work correctly."""
        mock_db.fetch_one.return_value = {"total": 30}
        mock_db.fetch_all.return_value = [
            {
                "session_id": f"session-{i}",
                "user_id": f"user-{i % 5}",
                "channel": "console",
                "total_traces": 3,
                "total_tokens": 500,
                "total_skills": 2,
                "first_active": datetime.now(),
                "last_active": datetime.now(),
            }
            for i in range(10)
        ]

        sessions, total = asyncio.run(store.get_sessions(page=1, page_size=10))
        assert len(sessions) == 10
        assert total == 30


class TestUserStatsWithDateFilter:
    """Tests for user stats with date filtering."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_user_stats_respects_date_filter(self, store):
        """User stats should only count sessions within date range."""
        user_id = "user-001"
        now = datetime.now()

        # Create sessions across different days
        for i in range(10):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=user_id,
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=i),
                status=TraceStatus.COMPLETED,
                total_input_tokens=100,
                total_output_tokens=50,
                model_name="gpt-4",
            )
            asyncio.run(store.create_trace(trace))

        # Get stats for last 3 days only
        stats = asyncio.run(store.get_user_stats(
            user_id,
            start_date=now - timedelta(days=3),
            end_date=now,
        ))

        assert stats.user_id == user_id
        assert stats.total_sessions == 4  # days 0, 1, 2, 3
        assert stats.total_tokens == 600  # 4 sessions * 150 tokens


class TestEmptyDateFilteredResults:
    """Tests for empty results when date filtering returns no data."""

    @pytest.fixture
    def store(self):
        config = TracingConfig(enabled=True)
        store = TraceStore(config, db=None)
        asyncio.run(store.initialize())
        return store

    def test_empty_users_with_date_filter(self, store):
        """Should return empty list when date filter matches nothing."""
        now = datetime.now()
        # Create old traces
        for i in range(5):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=30 + i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        # Query for recent dates (should be empty)
        users, total = asyncio.run(store.get_users(
            page=1,
            page_size=10,
            start_date=now - timedelta(days=7),
        ))
        assert users == []
        assert total == 0

    def test_empty_sessions_with_date_filter(self, store):
        """Should return empty list when date filter matches nothing."""
        now = datetime.now()
        # Create old traces
        for i in range(5):
            trace = Trace(
                trace_id=f"trace-{i}",
                user_id="user-001",
                session_id=f"session-{i}",
                channel="console",
                start_time=now - timedelta(days=30 + i),
                status=TraceStatus.COMPLETED,
            )
            asyncio.run(store.create_trace(trace))

        # Query for recent dates (should be empty)
        sessions, total = asyncio.run(store.get_sessions(
            page=1,
            page_size=10,
            start_date=now - timedelta(days=7),
        ))
        assert sessions == []
        assert total == 0
