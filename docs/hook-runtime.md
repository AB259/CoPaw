# Unified Agent Hook Runtime 使用说明

Unified Agent Hook Runtime 允许租户或 Agent 在关键生命周期事件上执行自定义策略，用于观察、补充上下文、修改工具输入、阻断请求或触发审批。当前 MVP 支持两类 handler：

- `command`：在本地租户 workspace 内执行命令，HookContext JSON 从 stdin 传入。
- `http`：将 HookContext JSON 作为 POST body 发送到远端 HTTP endpoint。

当前支持的事件：

| 事件 | 触发时机 | 常见用途 |
| --- | --- | --- |
| `SessionStart` | Agent 本轮请求准备完成、正式运行前 | 注入系统上下文、记录会话启动 |
| `UserPromptSubmit` | 用户 prompt 进入命令分发和推理前 | 阻断敏感 prompt、设置 session title、补充上下文 |
| `PreToolUse` | 工具调用执行前 | allow/deny/ask、替换工具输入、审计工具调用 |
| `PostToolUse` | 工具成功执行后 | 记录工具输出、补充后续上下文 |
| `PostToolUseFailure` | 工具执行失败后 | 记录错误、补充失败诊断上下文 |
| `Stop` | Agent 生成最终回复后、turn 完成前 | 最终检查、记录结束事件、补充后续上下文 |

## 配置位置

### 租户级配置

租户级 hooks 配置在每个租户自己的 `config.json` 根节点下：

```text
~/.swe/<tenant_id>/config.json
```

默认租户示例：

```text
~/.swe/default/config.json
```

如果启动参数或请求的租户是 `default_RMASSIST`，则配置路径是：

```text
~/.swe/default_RMASSIST/config.json
```

### Agent 级配置

Agent 级 hooks 使用同样的配置结构，放在对应 workspace 的 `agent.json` 内：

```text
~/.swe/<tenant_id>/workspaces/<workspace_id>/agent.json
```

运行时会在每个事件边界重新解析 tenant hooks、agent hooks 和 session overlay，生成本次事件的不可变执行计划。

### Skill 级配置

启用后的 workspace skill 可以在自身目录声明 session-scoped hooks：

```text
~/.swe/<tenant_id>/workspaces/<workspace_id>/skills/<skill_name>/
├── SKILL.md
├── hooks/
│   └── hooks.json
└── scripts/
    └── check.py
```

运行时只读取 `hooks/hooks.json`，不会读取 `hooks/` 下的其他配置文件。Skill hooks 在当前会话中首次激活该 skill 后加载，后续事件边界才会看到这些 handler；已经解析完成的 in-flight 事件计划不会被改写。

Skill hook 使用同样的 `HookConfig` 结构，但有额外边界：

- handler id 和 matcher group id 会被命名空间化为 `skill:<skill_name>:<id>`。
- command handler 必须使用 `argv`，不能使用 shell-string `command`。
- command handler 必须且只能引用一个位于同一 skill `scripts/` 目录下的脚本。
- 允许 `argv` 中出现 `python` 这类解释器命令；脚本参数会在加载时改写为解析后的绝对路径。
- command handler 不能声明 literal `env`。
- http handler 必须命中租户配置 `security.skill_hook_http.approved_urls` 中的精确 URL。
- skill-owned http handler 不能声明 literal `headers` 或 `allowedEnvVars`，只能使用 `headerSecretRefs`，并在执行时从当前 effective tenant 的密钥作用域解析。

最小 skill hook 示例：

```json
{
  "enabled": true,
  "events": {
    "PreToolUse": [
      {
        "id": "shell-policy",
        "matcher": {
          "tools": ["execute_shell_command"]
        },
        "hooks": [
          {
            "id": "check-shell",
            "type": "command",
            "argv": ["python", "scripts/check.py"],
            "timeout": 5,
            "failPolicy": "block"
          }
        ]
      }
    ]
  }
}
```

如果需要 skill-owned HTTP hook，租户配置需显式批准 endpoint：

```json
{
  "security": {
    "skill_hook_http": {
      "approved_urls": ["https://policy.example.com/hooks/skill"]
    }
  }
}
```

## 最小配置结构

`hooks` 放在 JSON 根节点下：

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
              "timeout": 5,
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

配置结构是：

```text
hooks.enabled
hooks.events.<HookEventName>[]          # matcher group
hooks.events.<HookEventName>[].matcher  # 可选匹配器
hooks.events.<HookEventName>[].hooks[]  # handler 列表
```

## Handler 通用字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | handler 唯一 ID。session overlay 和 once 状态都依赖它。 |
| `type` | 是 | 当前只支持 `command` 和 `http`。 |
| `if` | 否 | 受限表达式。返回 false 时跳过该 handler。 |
| `timeout` | 否 | 单个 handler 超时时间，单位秒，默认 `10`。 |
| `statusMessage` | 否 | 阻断或审批时可用于展示的状态文字。 |
| `once` | 否 | 为 true 时，同一租户、用户、session、事件、handler 只执行一次。 |
| `failPolicy` | 否 | handler 失败时策略：`allow` 或 `block`，默认 `allow`。 |

`if` 表达式支持简单比较、布尔运算、列表 membership 和 dict/属性读取，例如：

```json
{
  "if": "tool_name == 'execute_shell_command'"
}
```

## Matcher

当前 matcher 支持按工具名过滤：

```json
{
  "matcher": {
    "tools": ["execute_shell_command", "read_file"]
  }
}
```

如果不写 `matcher` 或 `matcher.tools` 为空，则匹配该事件下的所有调用。

## HookContext

handler 收到的输入是 HookContext JSON。`command` handler 从 stdin 读取，`http` handler 从 POST body 读取。

每个事件都有的字段：

| 字段 | 说明 |
| --- | --- |
| `session_id` | 当前 session ID |
| `transcript_path` | session state/transcript 路径 |
| `cwd` | 当前工作目录 |
| `hook_event_name` | 当前事件名 |
| `tenant_id` | 请求租户 ID |
| `effective_tenant_id` | 实际生效租户 ID |
| `user_id` | 用户 ID |
| `agent_id` | Agent ID |
| `channel` | 请求通道 |

常见可选字段：

| 字段 | 说明 |
| --- | --- |
| `workspace_dir` | 当前 workspace 路径 |
| `chat_id` | chat ID |
| `turn_id` | turn ID |
| `source_id` | 来源侧 ID |
| `agent_type` | Agent 类型 |
| `permission_mode` | 权限模式 |
| `effort.level` | reasoning effort |

事件字段：

| 字段 | 适用事件 | 说明 |
| --- | --- | --- |
| `source` | `SessionStart` | `startup`、`resume`、`clear`、`compact` |
| `model` | `SessionStart` | 当前激活模型标签 |
| `prompt` | `UserPromptSubmit`、`Stop` | 用户 prompt |
| `tool_name` | tool 事件 | 工具名 |
| `tool_input` | tool 事件 | 工具输入 |
| `tool_use_id` | tool 事件 | 工具调用 ID |
| `tool_response` | `PostToolUse` | 工具成功输出 |
| `error` | `PostToolUseFailure` | 工具错误信息 |

注意：不同工具的 `tool_input` 字段由工具签名决定。例如 `execute_shell_command` 的命令字段是 `command`，不是 `cmd`：

```json
{
  "tool_name": "execute_shell_command",
  "tool_input": {
    "command": "echo hello"
  }
}
```

## Command Handler

command handler 配置示例：

```json
{
  "id": "pretool-demo",
  "type": "command",
  "argv": ["python", "hooks/demo_hook.py"],
  "timeout": 5,
  "failPolicy": "block"
}
```

`argv` 和脚本路径建议使用相对路径，并把脚本放在当前 Agent workspace 内，例如：

```text
~/.swe/default_RMASSIST/workspaces/default/hooks/demo_hook.py
```

运行时 cwd 是当前 workspace，所以配置中可以写：

```json
{
  "argv": ["python", "hooks/demo_hook.py"]
}
```

安全约束：

- command handler 的 cwd 必须在当前租户 workspace 内。
- `argv` 中的绝对路径如果指向 workspace 外会被拒绝。
- shell command 也会经过路径边界校验。
- MVP 不支持 command `async` 和 `asyncRewake`。

退出码语义：

| 退出码 | 语义 |
| --- | --- |
| `0` | 成功，stdout 如果非空必须是 JSON object。 |
| `2` | 阻断事件，不按成功 HookResult 解析 stdout。 |
| 其他非零 | handler 失败，按 `failPolicy` 决定 allow/block。 |

## HTTP Handler

HTTP handler 配置示例：

```json
{
  "id": "remote-policy",
  "type": "http",
  "url": "https://policy.example.com/hooks/pre-tool",
  "headers": {
    "X-Hook-Source": "swe"
  },
  "headerSecretRefs": {
    "Authorization": "HOOK_AUTH_TOKEN"
  },
  "timeout": 5,
  "failPolicy": "block"
}
```

HTTP 语义：

| 响应 | 语义 |
| --- | --- |
| `2xx` | 成功，body 如果非空必须是 JSON object。 |
| `409` / `422` | 当 body 没有显式 HookResult 时，映射为 block。 |
| 其他状态码 | handler 失败，按 `failPolicy` 处理。 |
| 超时 | handler 失败，按 `failPolicy` 处理。 |

`headerSecretRefs` 会通过当前 effective tenant 的环境/密钥配置解析，不会写入 session state。

## Handler 输出

handler 输出必须是 JSON object。常见输出如下。

### 允许工具

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow",
    "permissionDecisionReason": "allowed by policy"
  }
}
```

### 拒绝工具

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "deny",
    "permissionDecisionReason": "dangerous command"
  }
}
```

### 请求用户审批

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "ask",
    "permissionDecisionReason": "please approve this command"
  }
}
```

`ask` 当前复用 Tool Guard 审批链路。前端会显示审批卡片，用户点击同意相当于发送 `/approve`，点击拒绝相当于发送 `/deny`。

注意：审批通过后会重放原工具调用，重放仍然会再次进入 `PreToolUse`。如果 hook 总是对同一命令返回 `ask`，可能形成重复审批。建议使用 `once: true`，或在 hook 策略里避免对已审批场景重复 ask。

### 阻断事件

```json
{
  "decision": "block",
  "reason": "blocked by tenant policy"
}
```

### 停止当前流程

```json
{
  "continue": false,
  "stopReason": "stop requested by hook"
}
```

### 注入额外上下文

```json
{
  "hookSpecificOutput": {
    "additionalContext": "policy engine observed this event"
  }
}
```

`additionalContext` 会带上 handler id，并传递给后续运行路径：

- `UserPromptSubmit` / `SessionStart`：加入当前 Agent env context。
- `PostToolUse` / `PostToolUseFailure`：写入 Agent memory，供后续推理看到。
- `Stop`：可写入 Agent memory。

### 修改工具输入

仅 `PreToolUse` 的 `updatedInput` 会被应用。它是整个工具输入对象的替换，不是 patch 或 deep merge：

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow",
    "updatedInput": {
      "command": "echo replaced-by-hook"
    }
  }
}
```

如果多个 handler 同时返回 `updatedInput`，runtime 会阻断事件，避免并发顺序导致不确定结果。

### 设置 session title

`UserPromptSubmit` 可以返回 session title：

```json
{
  "hookSpecificOutput": {
    "sessionTitle": "Hook Demo Session"
  }
}
```

## 完整本地示例

下面的示例可验证 `allow`、`deny`、`ask`、`block`、`updatedInput`、`additionalContext`。

### 1. 创建脚本

将脚本放到当前租户 workspace 内：

```text
~/.swe/default_RMASSIST/workspaces/default/hooks/demo_hook.py
```

脚本内容：

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys

ctx = json.load(sys.stdin)
event = ctx.get("hook_event_name")
tool_name = ctx.get("tool_name")
tool_input = ctx.get("tool_input") or {}
command = tool_input.get("command") or tool_input.get("cmd", "")
prompt = ctx.get("prompt", "")

if event == "UserPromptSubmit":
    if "hook-block-prompt" in prompt:
        print(json.dumps({
            "decision": "block",
            "reason": "UserPromptSubmit hook blocked this prompt",
        }))
    else:
        print(json.dumps({
            "hookSpecificOutput": {
                "sessionTitle": "Hook Demo Session",
                "additionalContext": "User prompt was inspected by demo hook",
            },
        }))
    raise SystemExit(0)

if event == "PreToolUse" and tool_name == "execute_shell_command":
    if "deny-hook" in command:
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "Denied by PreToolUse demo hook",
            },
        }))
    elif "ask-hook" in command:
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "ask",
                "permissionDecisionReason": "Ask user before running this command",
            },
        }))
    elif "block-hook" in command:
        print(json.dumps({
            "decision": "block",
            "reason": "Blocked by top-level hook decision",
        }))
    elif "update-hook" in command:
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "allow",
                "permissionDecisionReason": "Input replaced by hook",
                "updatedInput": {
                    "command": "echo replaced-by-pretooluse-hook",
                },
            },
        }))
    else:
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "allow",
                "permissionDecisionReason": "Allowed by demo hook",
                "additionalContext": "PreToolUse allowed shell command",
            },
        }))
    raise SystemExit(0)

if event == "PostToolUse":
    print(json.dumps({
        "hookSpecificOutput": {
            "additionalContext": "PostToolUse observed successful tool execution",
        },
    }))
    raise SystemExit(0)

if event == "PostToolUseFailure":
    print(json.dumps({
        "hookSpecificOutput": {
            "additionalContext": "PostToolUseFailure observed tool error: "
            + str(ctx.get("error", "")),
        },
    }))
    raise SystemExit(0)

if event == "Stop":
    print(json.dumps({
        "hookSpecificOutput": {
            "additionalContext": "Stop hook ran before turn completion",
        },
    }))
    raise SystemExit(0)

print("{}")
```

### 2. 配置租户 config.json

将以下内容合并到 `~/.swe/default_RMASSIST/config.json` 根节点：

```json
{
  "hooks": {
    "enabled": true,
    "events": {
      "UserPromptSubmit": [
        {
          "id": "prompt-demo",
          "hooks": [
            {
              "id": "prompt-demo-hook",
              "type": "command",
              "argv": ["python", "hooks/demo_hook.py"],
              "timeout": 5,
              "failPolicy": "block"
            }
          ]
        }
      ],
      "PreToolUse": [
        {
          "id": "shell-demo",
          "matcher": {
            "tools": ["execute_shell_command"]
          },
          "hooks": [
            {
              "id": "pretool-demo-hook",
              "type": "command",
              "argv": ["python", "hooks/demo_hook.py"],
              "if": "tool_name == 'execute_shell_command'",
              "timeout": 5,
              "statusMessage": "Running PreToolUse demo hook",
              "failPolicy": "block"
            }
          ]
        }
      ],
      "PostToolUse": [
        {
          "id": "posttool-demo",
          "matcher": {
            "tools": ["execute_shell_command"]
          },
          "hooks": [
            {
              "id": "posttool-demo-hook",
              "type": "command",
              "argv": ["python", "hooks/demo_hook.py"],
              "timeout": 5,
              "failPolicy": "allow"
            }
          ]
        }
      ],
      "PostToolUseFailure": [
        {
          "id": "posttool-failure-demo",
          "matcher": {
            "tools": ["execute_shell_command"]
          },
          "hooks": [
            {
              "id": "posttool-failure-demo-hook",
              "type": "command",
              "argv": ["python", "hooks/demo_hook.py"],
              "timeout": 5,
              "failPolicy": "allow"
            }
          ]
        }
      ],
      "Stop": [
        {
          "id": "stop-demo",
          "hooks": [
            {
              "id": "stop-demo-hook",
              "type": "command",
              "argv": ["python", "hooks/demo_hook.py"],
              "timeout": 5,
              "failPolicy": "allow"
            }
          ]
        }
      ]
    }
  }
}
```

如果服务已启动，建议重启服务，确保运行进程使用最新代码和最新配置。

## 如何验证

### 1. 验证配置可加载

在项目根目录运行：

```bash
venv/bin/python -c 'from pathlib import Path; from swe.config.utils import load_config; cfg=load_config(Path("/Users/shixiangyi/.swe/default_RMASSIST/config.json")); print(cfg.hooks.enabled); print(sorted(str(k) for k in cfg.hooks.events.keys()))'
```

预期看到：

```text
True
['HookEventName.POST_TOOL_USE', 'HookEventName.POST_TOOL_USE_FAILURE', 'HookEventName.PRE_TOOL_USE', 'HookEventName.STOP', 'HookEventName.USER_PROMPT_SUBMIT']
```

### 2. 直接验证 command handler 脚本

在 workspace 目录下运行：

```bash
printf '%s' '{"session_id":"s1","transcript_path":"","cwd":"/Users/shixiangyi/.swe/default_RMASSIST/workspaces/default","hook_event_name":"PreToolUse","tenant_id":"default_RMASSIST","effective_tenant_id":"default_RMASSIST","user_id":"u1","agent_id":"default","channel":"console","tool_name":"execute_shell_command","tool_input":{"command":"echo deny-hook"},"tool_use_id":"t1"}' | python hooks/demo_hook.py
```

预期输出包含：

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "deny"
  }
}
```

### 3. 验证 runtime 决策

在项目根目录运行：

```bash
venv/bin/python -c 'import asyncio
from pathlib import Path
from swe.config.utils import load_config
from swe.agents.hook_runtime import HookRuntime
from swe.agents.hook_runtime.models import HookConfig, HookContext, HookEventName
async def main():
    cfg = load_config(Path("/Users/shixiangyi/.swe/default_RMASSIST/config.json"))
    workspace = Path("/Users/shixiangyi/.swe/default_RMASSIST/workspaces/default")
    for command in ["echo deny-hook", "echo ask-hook", "echo update-hook", "echo hello"]:
        ctx = HookContext(
            session_id="s1",
            transcript_path="",
            cwd=str(workspace),
            hook_event_name=HookEventName.PRE_TOOL_USE,
            tenant_id="default_RMASSIST",
            effective_tenant_id="default_RMASSIST",
            user_id="u1",
            agent_id="default",
            channel="console",
            workspace_dir=str(workspace),
            tool_name="execute_shell_command",
            tool_input={"command": command},
            tool_use_id="t1",
        )
        result = await HookRuntime(
            tenant_config=cfg.hooks,
            agent_config=HookConfig(),
        ).emit(ctx, workspace_dir=workspace)
        print(command, "=>", result.decision, result.reason, result.updated_input)
asyncio.run(main())'
```

预期：

```text
echo deny-hook => HookDecision.DENY ...
echo ask-hook => HookDecision.ASK ...
echo update-hook => HookDecision.ALLOW ... {'command': 'echo replaced-by-pretooluse-hook'}
echo hello => HookDecision.ALLOW ...
```

### 4. 在前端或会话中验证

让 Agent 执行：

```text
请执行 echo hello
```

预期：工具正常执行。

```text
请执行 echo deny-hook
```

预期：`PreToolUse` 返回 deny，工具不执行。

```text
请执行 echo ask-hook
```

预期：出现审批卡片。点击同意会发送 `/approve`，点击拒绝会发送 `/deny`。

```text
请执行 echo update-hook
```

预期：实际执行命令被替换为：

```bash
echo replaced-by-pretooluse-hook
```

```text
hook-block-prompt
```

预期：`UserPromptSubmit` 在正常推理前阻断 prompt。

## Session Overlay

session state 可包含 `hook_overlay`：

```json
{
  "hook_overlay": {
    "entries": [
      {
        "hookId": "pretool-demo-hook",
        "enabled": false,
        "expiresAt": "2026-05-12T10:00:00Z",
        "reason": "temporary debugging"
      }
    ],
    "once_executed": {
      "default_RMASSIST:default:session-1:PreToolUse:pretool-demo-hook": true
    }
  }
}
```

overlay 只能影响当前 effective tenant 或 agent config 中已存在的 hook id。过期 entry 会被忽略。`once_executed` 由 runtime 写回 session state。

## 决策合并规则

同一事件匹配到多个 handler 时会并发执行，但合并按配置顺序 deterministic 处理。

优先级：

```text
continue:false > block/deny > ask > allow > none
```

其他规则：

- `additionalContext` 按 handler 配置顺序拼接。
- `hookSpecificOutput` 按 handler id 保存。
- `updatedInput` 只允许单 writer；多个 handler 返回时会 block。
- 等价 handler 在同一事件计划内会去重，避免重复副作用。

## 常见问题

### 配置后没有生效

检查以下几点：

1. 配置是否写在实际请求的租户目录下，例如 `~/.swe/default_RMASSIST/config.json`。
2. 当前运行服务是否已重启，且使用的是包含 hook runtime 的代码版本。
3. `hooks.enabled` 是否为 `true`。
4. `matcher.tools` 是否匹配真实工具名。
5. handler 脚本是否位于当前 workspace 内。
6. command handler 的路径是否使用 workspace 内相对路径。

### deny/ask 没触发，命令仍然执行

优先检查 `tool_input` 字段名。`execute_shell_command` 使用：

```json
{
  "command": "echo hello"
}
```

不是：

```json
{
  "cmd": "echo hello"
}
```

### ask 后一直重复审批

审批通过后的工具重放仍会进入 `PreToolUse`。如果 hook 对同一条件总是返回 `ask`，会再次触发审批。处理方式：

- 给 handler 配置 `once: true`。
- 或在 hook 逻辑中根据上下文/外部状态避免重复 ask。

### command hook 报路径越界

command hook 受租户 workspace 边界保护。将脚本放到当前 workspace 下，并使用相对路径：

```json
{
  "argv": ["python", "hooks/demo_hook.py"]
}
```

不要写 workspace 外绝对路径，例如 `/usr/bin/python` 后接 workspace 外脚本。

### handler 输出 JSON 解析失败

退出码 `0` 时 stdout 必须为空或合法 JSON object。调试日志不要写 stdout，建议写 stderr。

### 远端 HTTP hook 没收到密钥

确认密钥名在当前 effective tenant 的环境/密钥配置中存在，并且 `headerSecretRefs` 指向正确名称。
