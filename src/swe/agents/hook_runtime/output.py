# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from .models import HookDecision, HookHandlerResult, HookOutput


def normalize_hook_output(
    *,
    handler_id: str,
    order: int,
    raw_output: dict[str, Any],
) -> HookHandlerResult:
    output = HookOutput.model_validate(raw_output)
    decision = HookDecision.NONE
    reason = output.reason or ""

    if output.continue_ is False:
        decision = HookDecision.STOP
        reason = output.stop_reason or reason or "Hook requested stop"
    elif output.decision == "block":
        decision = HookDecision.BLOCK
        reason = reason or "Hook blocked the event"

    specific = output.hook_specific_output or {}
    permission_decision = specific.get("permissionDecision")
    permission_reason = specific.get("permissionDecisionReason")
    if permission_decision in {"allow", "deny", "ask"}:
        decision = HookDecision(permission_decision)
        reason = str(permission_reason or reason or "")
    elif permission_decision == "defer":
        decision = HookDecision.BLOCK
        reason = "Hook permissionDecision=defer is not supported"

    return HookHandlerResult(
        handler_id=handler_id,
        order=order,
        output=output,
        decision=decision,
        reason=reason,
    )
