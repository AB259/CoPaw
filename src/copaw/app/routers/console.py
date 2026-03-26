# -*- coding: utf-8 -*-
"""Console API: push messages for cron text bubbles on the frontend."""

from fastapi import APIRouter, Header, Query


router = APIRouter(prefix="/console", tags=["console"])


@router.get("/push-messages")
async def get_push_messages(
    session_id: str | None = Query(None, description="Optional session id"),
    user_id: str = Header(default="default", alias="x-user-id"),
):
    """
    Return pending push messages. All read operations consume messages.
    With user_id only: returns and removes recent messages for that user.
    With user_id and session_id: returns and removes messages for that user's session.
    """
    from ..console_push_store import take, get_recent

    if session_id:
        messages = await take(user_id, session_id)
    else:
        messages = await get_recent(user_id)
    return {"messages": messages}
