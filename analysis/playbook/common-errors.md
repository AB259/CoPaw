# 常见报错

本文档只收录仓库中已经出现过、且有明确入口可追的高频报错。

## 长 MCP 调用期间 console SSE 被静默断开

### 症状

- MCP 工具调用耗时 10 秒以上时，前端 console 会话中断
- `streamable_http` MCP 本身还在执行，但 `/console/chat` 长时间没有任何 SSE 输出
- 日志可见运行被取消，例如：
  - `query_handler: <session_id> cancelled!`
  - `Runner finally block executing for session <session_id>`

### 典型原因

- 外层 `/console/chat` SSE 在长时间无事件期间没有发送心跳帧
- 代理、Ingress 或客户端对 10 到 15 秒静默连接执行 idle timeout
- 即使后端任务未失败，HTTP 流也会先被外层网络链路掐断
- `streamable_http` MCP 如果走到默认 `httpx` timeout，可能在读阶段约 5 秒无新字节时先超时或触发中断链路

### 第一落点

- [src/swe/app/routers/console.py](/Users/shixiangyi/code/Swe/src/swe/app/routers/console.py)
- 重点看 `post_console_chat()` 和 `_stream_with_keepalive()`
- [src/swe/app/runner/runner.py](/Users/shixiangyi/code/Swe/src/swe/app/runner/runner.py)
- 重点看 `_create_mcp_client_with_headers()` 是否给 `streamable_http` MCP 显式配置 `httpx.Timeout`

### 第一阶段处理

- 在 `/console/chat` 的 SSE 输出层补 comment 心跳，例如 `: keep-alive\n\n`
- 心跳周期要小于最短代理 idle timeout，当前实现默认 5 秒
- 响应头显式加 `X-Accel-Buffering: no`，避免代理缓冲导致心跳帧无法及时刷出

### 边界说明

- 这一阶段只解决“外层 SSE 静默断连”
- 不包含 MCP 内部执行进度透传；如果希望前端看到“工具执行中”，需要后续把 MCP progress/event 映射进 `TaskTracker` 或 SSE 事件流

## Console 切换运行中会话时 reconnect 返回 404

### 症状

- 两个 console 会话同时流式输出，前端在会话间快速切换
- 前端发起 `/api/console/chat` reconnect 请求，body 里 `session_id` 可能是本地时间戳格式
- 后端返回 404，detail 为 `No running chat for this session`

### 典型原因

- Console 前端先创建本地时间戳 session，再等待后端创建真实 `chat.id`
- 切换会话会断开当前 SSE，并用 `reconnect=true` 重新附着到后端 `TaskTracker`
- reconnect 请求可能早于后端完成 `session_id -> chat.id -> run_key` 注册，第一次查询映射或 active run 时会查不到

### 第一落点

- [src/swe/app/routers/console.py](/Users/shixiangyi/code/Swe/src/swe/app/routers/console.py)
- 重点看 `_attach_reconnect_queue()` 对 `session_id`、`chat.id` 和 `TaskTracker.attach()` 的处理
- [src/swe/app/runner/task_tracker.py](/Users/shixiangyi/code/Swe/src/swe/app/runner/task_tracker.py)
- 重点看 run_key 是否使用 `ChatSpec.id`
- [console/src/pages/Chat/sessionApi/index.ts](/Users/shixiangyi/code/Swe/console/src/pages/Chat/sessionApi/index.ts)
- 重点看本地时间戳 session 与真实 `chat.id` 的映射

### 第一阶段处理

- reconnect 不要只查一次；在短窗口内重试解析 `session_id -> chat.id` 并附着 active run
- 保持 run_key 统一为 `ChatSpec.id`，不要把前端本地时间戳直接当作 `TaskTracker` key
- 如果问题仍出现，抓取同一请求的 `session_id`、解析出的 `chat_id`、`TaskTracker.list_active_tasks()` 三项证据

## Console 手动停止后会话仍在运行

### 症状

- 前端点击停止按钮后发起 `POST /api/console/chat/stop?chat_id=...`
- 接口返回 200，但响应可能是 `{"stopped": false}`
- 后端 Agent 任务仍在继续输出或继续执行工具调用

### 典型原因

- `TaskTracker` 的运行键必须是 `ChatSpec.id`，也就是后端真实 `chat_id`
- Console 前端新会话会先使用本地时间戳 / 逻辑 `session_id`，真实 `chat_id` 需要等后端创建会话后解析
- 手动取消链路如果只传 `session_id`，或把逻辑 `session_id` 当成 `chat_id`，后端会找不到正在运行的 `run_key`

### 第一落点

- [console/src/components/agentscope-chat/AgentScopeRuntimeWebUI/core/Chat/hooks/useChatRequest.tsx](/Users/shixiangyi/code/Swe/console/src/components/agentscope-chat/AgentScopeRuntimeWebUI/core/Chat/hooks/useChatRequest.tsx)
- 重点看 `cancelActiveRequest()` 是否透传 `activeRequestOwner.chatId`
- [console/src/pages/Chat/index.tsx](/Users/shixiangyi/code/Swe/console/src/pages/Chat/index.tsx)
- 重点看 `resolveRequestChatId()` 是否优先使用 `data.chat_id`
- [src/swe/app/routers/console.py](/Users/shixiangyi/code/Swe/src/swe/app/routers/console.py)
- 重点看 `post_console_chat_stop()` 是否把逻辑 session 解析成 `ChatSpec.id`

### 第一阶段处理

- 前端手动 cancel 必须携带 `session_id`、`logical_session_id` 和真实 `chat_id`
- 后端 stop 路由应优先按 `chat_id` 识别真实 ChatSpec；识别不到时再按 console `session_id` 解析真实 `chat_id`
- 排查时对比三项：请求 URL 中的 `chat_id`、`chat_manager.get_chat_id_by_session()` 解析结果、`TaskTracker` 当前 active run keys
