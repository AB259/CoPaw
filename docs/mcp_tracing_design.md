# MCP 调用统计设计方案

## 背景

当前 tracing 系统记录了所有 tool 调用，但没有区分：
1. 普通工具 vs MCP 工具
2. MCP 工具属于哪个 MCP 服务器
3. Skill 调用了哪些 MCP 工具

## 数据模型变更

### 1. Span 模型增加 MCP 字段

```python
# src/copaw/tracing/models.py

class Span(BaseModel):
    # 现有字段...
    tool_name: Optional[str] = Field(default=None, description="Tool name")
    skill_name: Optional[str] = Field(default=None, description="Skill name")

    # 新增字段
    mcp_server: Optional[str] = Field(
        default=None,
        description="MCP server name if this tool is from MCP"
    )
```

### 2. 新增 MCP 使用统计模型

```python
# src/copaw/tracing/models.py

class MCPToolUsage(BaseModel):
    """MCP tool usage statistics."""

    tool_name: str
    mcp_server: str  # MCP 服务器名称
    count: int = 0
    avg_duration_ms: int = 0
    error_count: int = 0

class MCPServerUsage(BaseModel):
    """MCP server usage statistics."""

    server_name: str
    tool_count: int = 0  # 该服务器提供的工具数量
    total_calls: int = 0  # 总调用次数
    avg_duration_ms: int = 0
    error_count: int = 0
    tools: list[MCPToolUsage] = Field(default_factory=list)

class SkillMCPUsage(BaseModel):
    """MCP tools called by a specific skill."""

    skill_name: str
    mcp_tools: list[MCPToolUsage] = Field(default_factory=list)
    total_calls: int = 0
```

### 3. OverviewStats 增加 MCP 统计

```python
class OverviewStats(BaseModel):
    # 现有字段...
    top_tools: list[ToolUsage] = Field(default_factory=list)
    top_skills: list[SkillUsage] = Field(default_factory=list)

    # 新增字段
    top_mcp_tools: list[MCPToolUsage] = Field(default_factory=list)
    mcp_servers: list[MCPServerUsage] = Field(default_factory=list)
```

### 4. SessionStats 增加 MCP 统计

```python
class SessionStats(BaseModel):
    # 现有字段...

    # 新增字段
    mcp_tools_used: list[MCPToolUsage] = Field(default_factory=list)
```

## API 变更

### 1. 新增 API 端点

```
GET /tracing/mcp/tools          # 获取所有 MCP 工具统计
GET /tracing/mcp/servers        # 获取 MCP 服务器统计
GET /tracing/mcp/skill/{skill}  # 获取特定 Skill 的 MCP 调用统计
```

## TraceStore 变更

### 1. 数据库查询

需要修改 `_db_get_overview_stats` 和内存查询方法，增加 MCP 工具的统计：

```python
# 按 mcp_server 分组统计
mcp_tool_query = """
    SELECT tool_name,
           MAX(mcp_server) as mcp_server,
           COUNT(*) as count,
           AVG(duration_ms) as avg_duration,
           SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count
    FROM swe_tracing_spans
    WHERE start_time >= %s AND start_time <= %s
      AND event_type = 'tool_call_end'
      AND mcp_server IS NOT NULL
    GROUP BY tool_name
    ORDER BY count DESC
    LIMIT 10
"""
```

### 2. 内存存储

在 `_memory_get_overview_stats` 中增加 MCP 工具识别和统计：

```python
# 根据 mcp_server 字段区分 MCP 工具
mcp_tool_counts: dict[str, dict] = {}
for trace_id, spans in self._spans.items():
    for s in spans:
        if s.event_type == EventType.TOOL_CALL_END and s.tool_name:
            if s.mcp_server:  # MCP 工具
                key = f"{s.mcp_server}:{s.tool_name}"
                if key not in mcp_tool_counts:
                    mcp_tool_counts[key] = {
                        "tool_name": s.tool_name,
                        "mcp_server": s.mcp_server,
                        "count": 0, "duration": 0, "errors": 0
                    }
                mcp_tool_counts[key]["count"] += 1
                # ...
```

## Tracing Hook 变更

### 修改 TracingHook 以支持 MCP 标识

```python
# src/copaw/agents/hooks/tracing.py

async def on_tool_start(
    self,
    tool_name: str,
    tool_input: Optional[dict[str, Any]],
    tool_call_id: Optional[str] = None,
    mcp_server: Optional[str] = None,  # 新增参数
) -> str:
    # ...
    span_id = await manager.emit_tool_call_start(
        trace_id=self.trace_id,
        tool_name=tool_name,
        tool_input=tool_input,
        user_id=self.user_id,
        session_id=self.session_id,
        channel=self.channel,
        mcp_server=mcp_server,  # 传递 MCP 服务器名
    )
```

## 数据库表变更

### swe_tracing_spans 表增加字段

```sql
ALTER TABLE swe_tracing_spans
ADD COLUMN mcp_server VARCHAR(255) NULL
COMMENT 'MCP server name if this tool is from MCP';
```

## 前端页面变更

### 1. Overview 页面增加 MCP 统计卡片

```tsx
// 新增 MCP 工具调用统计卡片
<Col xs={24} lg={12}>
  <Card title={
    <span>
      <Plug size={16} style={{ marginRight: 8 }} />
      {t("analytics.topMCPTools", "Top MCP Tools")}
    </span>
  }>
    <Table
      dataSource={stats.top_mcp_tools}
      columns={mcpToolColumns}
      rowKey="tool_name"
      size="small"
      pagination={false}
    />
  </Card>
</Col>
```

### 2. 增加 MCP 服务器统计视图

```tsx
// 按 MCP 服务器分组的统计
interface MCPToolUsage {
  tool_name: string;
  mcp_server: string;
  count: number;
  avg_duration_ms: number;
  error_count: number;
}

const mcpToolColumns: ColumnsType<MCPToolUsage> = [
  {
    title: t("analytics.mcpServer", "MCP Server"),
    dataIndex: "mcp_server",
    key: "mcp_server",
    width: 120,
  },
  {
    title: t("analytics.tool", "Tool"),
    dataIndex: "tool_name",
    key: "tool_name",
  },
  {
    title: t("analytics.calls", "Calls"),
    dataIndex: "count",
    key: "count",
    sorter: (a, b) => a.count - b.count,
  },
  {
    title: t("analytics.avgDuration", "Avg Duration"),
    dataIndex: "avg_duration_ms",
    key: "avg_duration_ms",
    render: (v) => formatDuration(v),
  },
];
```

### 3. Session 详情页增加 MCP 调用

在 SessionStats 组件中展示该会话的 MCP 工具调用情况。

## 调用链追踪

### 如何识别 MCP 工具

有几种方式可以识别工具是否来自 MCP：

1. **在 Agent 中传递标识**：当工具通过 MCP 调用时，agent 知道工具来源
2. **通过工具名前缀**：某些 MCP 工具有特定命名模式
3. **通过工具元数据**：MCP 工具可能包含特定的 metadata

### 推荐方案

在 `react_agent.py` 的 `_act` 方法中，当调用工具时判断是否来自 MCP：

```python
# 在 _act 方法中
for tool_call in tool_calls:
    tool_name = tool_call.get("name", "")
    # 检查工具是否来自 MCP
    mcp_server = self._get_mcp_server_for_tool(tool_name)
    if mcp_server:
        await hook.on_tool_start(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call.get("id"),
            mcp_server=mcp_server,
        )
```

需要维护一个工具名到 MCP 服务器的映射：

```python
def _get_mcp_server_for_tool(self, tool_name: str) -> Optional[str]:
    """Get the MCP server name for a tool if it's from MCP."""
    # 工具注册时记录的来源信息
    return self._tool_to_mcp_server.get(tool_name)
```

## 实现步骤

1. **模型变更**：修改 `models.py` 增加 MCP 相关字段和模型
2. **数据库变更**：修改表结构增加 `mcp_server` 字段
3. **Store 变更**：修改 `store.py` 增加 MCP 统计查询方法
4. **Hook 变更**：修改 `tracing.py` hook 支持 MCP 标识
5. **Agent 变更**：修改 `react_agent.py` 在调用 MCP 工具时传递标识
6. **API 变更**：修改 `tracing.py` router 增加新端点
7. **前端变更**：修改 Overview 页面增加 MCP 统计展示
