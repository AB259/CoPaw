# -*- coding: utf-8 -*-
"""Manual test for MCP tools statistics."""
import sys
sys.path.insert(0, 'src')

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from copaw.tracing.config import TracingConfig
from copaw.tracing.models import EventType, Trace, TraceStatus, Span
from copaw.tracing.store import TraceStore


async def test_memory_mode_mcp_tools():
    """Test MCP tools in memory mode."""
    print("\n=== Testing Memory Mode MCP Tools ===")

    config = TracingConfig(enabled=True)
    store = TraceStore(config, db=None)
    await store.initialize()

    # Create trace
    trace = Trace(
        trace_id='trace-001',
        user_id='user-001',
        session_id='session-001',
        channel='console',
        start_time=datetime.now(),
        status=TraceStatus.COMPLETED,
    )
    await store.create_trace(trace)

    # Regular tool
    regular_span = Span(
        span_id='span-regular',
        trace_id='trace-001',
        name='regular_tool',
        event_type=EventType.TOOL_CALL_END,
        start_time=datetime.now(),
        user_id='user-001',
        session_id='session-001',
        channel='console',
        tool_name='regular_tool',
        duration_ms=100,
        mcp_server=None,
    )
    await store.create_span(regular_span)

    # MCP tool
    mcp_span = Span(
        span_id='span-mcp',
        trace_id='trace-001',
        name='mcp_tool',
        event_type=EventType.TOOL_CALL_END,
        start_time=datetime.now(),
        user_id='user-001',
        session_id='session-001',
        channel='console',
        tool_name='filesystem_read',
        duration_ms=200,
        mcp_server='filesystem',
    )
    await store.create_span(mcp_span)

    # Get overview stats
    stats = await store.get_overview_stats()

    print(f'top_tools: {[t.tool_name for t in stats.top_tools]}')
    print(f'top_mcp_tools: {[(t.tool_name, t.mcp_server) for t in stats.top_mcp_tools]}')
    print(f'mcp_servers: {[s.server_name for s in stats.mcp_servers]}')

    # Get session stats
    session_stats = await store.get_session_stats('session-001')
    print(f'tools_used: {[t.tool_name for t in session_stats.tools_used]}')
    print(f'mcp_tools_used: {[(t.tool_name, t.mcp_server) for t in session_stats.mcp_tools_used]}')

    # Verify
    assert len(stats.top_tools) == 1, f'Expected 1 regular tool, got {len(stats.top_tools)}'
    assert stats.top_tools[0].tool_name == 'regular_tool'
    assert len(stats.top_mcp_tools) == 1, f'Expected 1 MCP tool, got {len(stats.top_mcp_tools)}'
    assert len(session_stats.mcp_tools_used) == 1
    assert len(session_stats.tools_used) == 1

    print("Memory mode MCP tools test PASSED!")


async def test_database_mode_mcp_tools():
    """Test MCP tools in database mode with mock."""
    print("\n=== Testing Database Mode MCP Tools ===")

    mock_db = MagicMock()
    mock_db.is_connected = True
    mock_db.execute = AsyncMock()
    mock_db.execute_many = AsyncMock()
    mock_db.fetch_one = AsyncMock()
    mock_db.fetch_all = AsyncMock()
    mock_db.close = AsyncMock()

    config = TracingConfig(enabled=True)
    store = TraceStore(config, db=mock_db)
    await store.initialize()

    # Mock session stats queries
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

    # Mock query results in order
    mock_db.fetch_all.side_effect = [
        [],  # model_usage
        [    # tools_used (non-MCP)
            {
                "tool_name": "regular_tool",
                "count": 5,
                "avg_duration": 50.0,
                "error_count": 0,
            }
        ],
        [    # mcp_tools_used
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
        ],
        [],  # skills_used
    ]

    stats = await store.get_session_stats("session-001")

    print(f'tools_used: {[t.tool_name for t in stats.tools_used]}')
    print(f'mcp_tools_used: {[(t.tool_name, t.mcp_server) for t in stats.mcp_tools_used]}')

    assert len(stats.tools_used) == 1
    assert stats.tools_used[0].tool_name == "regular_tool"
    assert len(stats.mcp_tools_used) == 2
    assert stats.mcp_tools_used[0].tool_name == "read_file"
    assert stats.mcp_tools_used[0].mcp_server == "filesystem"

    print("Database mode MCP tools test PASSED!")


async def test_database_mode_overview_mcp():
    """Test MCP server grouping in database mode overview."""
    print("\n=== Testing Database Mode Overview MCP Servers ===")

    mock_db = MagicMock()
    mock_db.is_connected = True
    mock_db.execute = AsyncMock()
    mock_db.execute_many = AsyncMock()
    mock_db.fetch_one = AsyncMock()
    mock_db.fetch_all = AsyncMock()
    mock_db.close = AsyncMock()

    config = TracingConfig(enabled=True)
    store = TraceStore(config, db=mock_db)
    await store.initialize()

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

    mock_db.fetch_all.side_effect = [
        [],  # model_distribution
        [],  # top_tools
        [],  # top_skills
        [    # top_mcp_tools
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
        ],
        [],  # daily_trend
    ]

    stats = await store.get_overview_stats()

    print(f'mcp_tools count: {len(stats.top_mcp_tools)}')
    print(f'mcp_servers count: {len(stats.mcp_servers)}')
    for server in stats.mcp_servers:
        print(f'  {server.server_name}: {server.tool_count} tools, {server.total_calls} calls, {server.error_count} errors')

    assert len(stats.top_mcp_tools) == 3
    assert len(stats.mcp_servers) == 2

    fs_server = next(s for s in stats.mcp_servers if s.server_name == "filesystem")
    assert fs_server.tool_count == 2
    assert fs_server.total_calls == 15
    assert fs_server.error_count == 1

    print("Database mode overview MCP servers test PASSED!")


async def main():
    try:
        await test_memory_mode_mcp_tools()
        await test_database_mode_mcp_tools()
        await test_database_mode_overview_mcp()
        print("\n=== ALL TESTS PASSED ===")
    except Exception as e:
        print(f"\n!!! TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
