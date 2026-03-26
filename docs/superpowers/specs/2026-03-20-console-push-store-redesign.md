# Console Push Store Redesign

## Summary

Redesign `console_push_store.py` so that messages are consumed exactly once: any message returned by `get_recent()` or `take()` is immediately removed from storage.

## Current Behavior

- `get_recent()` returns recent messages **without removing them**
- `take()` returns and removes messages for a specific session
- Messages accumulate until explicitly taken, causing potential memory bloat

## New Behavior

All read operations are destructive: messages returned are immediately deleted from the store.

### API Changes

```python
async def get_recent(
    user_id: str | None = None,
    max_age_seconds: int = _MAX_AGE_SECONDS,
) -> List[Dict[str, Any]]
"""Return recent messages for the user and REMOVE them from storage."""

async def take(user_id: str | None, session_id: str) -> List[Dict[str, Any]]
"""Return all messages for the user/session and REMOVE them from storage."""

async def take_all(user_id: str | None = None) -> List[Dict[str, Any]]
"""Return all messages for the user and REMOVE them from storage."""
```

### Implementation Details

1. **Unified consumption model**: Both `get_recent()` and `take()` remove returned messages
2. **Time-based filtering in `get_recent`**: Only messages newer than `cutoff` are returned
3. **Session-based filtering in `take`**: Only messages matching the session_id are returned
4. **No state tracking**: Simple remove-on-read, no `consumed` flags or complex state machine
5. **Memory-only**: No persistence, remains in-memory store

### Data Flow

```
append() → [pending messages in store]
                ↓
    ┌───────────┴───────────┐
    ↓                       ↓
get_recent()            take()
(filter by time)      (filter by session)
    ↓                       ↓
[remove & return]    [remove & return]
```

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Empty store | Return empty list |
| No matching messages | Return empty list, store unchanged |
| Concurrent calls | Lock ensures atomicity, no double consumption |
| `get_recent` with old `max_age_seconds` | Returns and removes only messages within window |
| Messages never read | Remain in store until `get_recent` or `take` cleans them |

## Migration Notes

- Frontend code using `get_recent()` should not be affected functionally
- Message deduplication in frontend can potentially be simplified (no longer needed)

## Testing Considerations

1. Message appended → `get_recent` returns it → second `get_recent` returns empty
2. Message appended → `take` returns it → `get_recent` returns empty
3. Multiple sessions: `take(session_A)` only removes session A messages
4. Concurrent append and take operations remain safe
