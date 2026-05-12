# Unified Agent Hook Runtime

The unified hook runtime lets tenant and agent configuration observe, enrich,
or block selected agent lifecycle events. The MVP supports `command` and
`http` handlers.

## Tenant Config

Tenant-level hooks live in `config.json` under `hooks`:

```json
{
  "hooks": {
    "enabled": true,
    "events": {
      "PreToolUse": [
        {
          "id": "shell-tools",
          "matcher": {
            "tools": ["execute_shell_command"]
          },
          "hooks": [
            {
              "id": "audit-shell",
              "type": "command",
              "argv": ["python", "hooks/audit_shell.py"],
              "if": "tool_name == 'execute_shell_command'",
              "timeout": 3,
              "statusMessage": "Checking shell command",
              "failPolicy": "block"
            }
          ]
        }
      ]
    }
  }
}
```

Agent-level `agent.json` accepts the same `hooks` shape. Tenant hooks and
agent hooks are resolved at each event boundary.

## Session Overlay

Session state may include `hook_overlay`:

```json
{
  "hook_overlay": {
    "entries": [
      {
        "hookId": "audit-shell",
        "enabled": false,
        "expiresAt": "2026-05-12T10:00:00Z",
        "reason": "temporary debugging"
      }
    ],
    "once_executed": {
      "tenant-a:user-1:session-1:PreToolUse:audit-shell": true
    }
  }
}
```

Overlay entries can only affect hook ids already defined by the effective
tenant or agent config.

## Command Handlers

Command handlers receive the full `HookContext` JSON on stdin. Exit code `0`
parses stdout as a hook result. Exit code `2` blocks without treating stdout
as successful JSON.

```python
import json
import sys

ctx = json.load(sys.stdin)
tool_input = ctx.get("tool_input") or {}

if "rm -rf" in tool_input.get("cmd", ""):
    print("destructive command", file=sys.stderr)
    raise SystemExit(2)

print(json.dumps({
    "hookSpecificOutput": {
        "permissionDecision": "allow",
        "additionalContext": "shell command audited"
    }
}))
```

Command `cwd` and absolute argv paths must stay under the current tenant
workspace.

## HTTP Handlers

HTTP handlers receive `HookContext` as the POST JSON body. `2xx` responses
parse as hook results. `409` and `422` block when no explicit hook result is
returned.

```json
{
  "continue": true,
  "hookSpecificOutput": {
    "permissionDecision": "deny",
    "permissionDecisionReason": "blocked by policy"
  }
}
```

Returned `hookSpecificOutput.additionalContext` is preserved with the handler
id and made available to later runtime consumers.
