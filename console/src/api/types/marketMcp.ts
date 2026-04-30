/**
 * 市场 MCP 相关类型定义
 */

/** MCP 配置详情（脱敏展示） */
export interface MCPConfigDetail {
  /** 显示名称 */
  name: string;
  /** 描述 */
  description: string;
  /** MCP 传输类型 */
  transport: "stdio" | "streamable_http" | "sse";
  /** HTTP/SSE URL */
  url: string;
  /** HTTP headers（脱敏展示） */
  headers: Record<string, string>;
  /** stdio 命令 */
  command: string;
  /** 命令行参数 */
  args: string[];
  /** 环境变量（脱敏展示） */
  env: Record<string, string>;
  /** 工作目录 */
  cwd: string;
}

/** 市场 MCP 列表项 */
export interface MarketMCPItem {
  /** 市场 item ID */
  item_id: string;
  /** MCP client key */
  client_key: string;
  /** 显示名称 */
  name: string;
  /** 调用次数 */
  call_count: number;
  /** 使用人数 */
  user_count: number;
}

/** MCP 用户使用统计 */
export interface MCPUserStat {
  /** 用户 ID */
  user_id: string;
  /** 用户名 */
  user_name: string;
  /** 调用次数 */
  call_count: number;
}

/** 市场 MCP 详情 */
export interface MarketMCPDetail extends MarketMCPItem {
  /** MCP 配置（脱敏展示） */
  config: MCPConfigDetail;
  /** 用户使用统计列表 */
  user_stats: MCPUserStat[];
}

/** MCP 上传请求 */
export interface MCPUploadRequest {
  /** MCP client key */
  client_key: string;
  /** 显示名称 */
  name: string;
  /** 描述 */
  description?: string;
  /** 分类 ID */
  category_id?: number;
  /** 关联 BBK ID 列表 */
  bbk_ids?: string[];
  /** MCP 配置 */
  config: MCPConfigDetail;
}

/** MCP 分发请求 */
export interface MCPDistributeRequest {
  /** 市场 item ID */
  item_id: string;
  /** 目标用户 ID 列表 */
  target_user_ids: string[];
}

/** MCP 分发结果 */
export interface MCPDistributeResult {
  /** 用户 ID */
  user_id: string;
  /** 是否成功 */
  success: boolean;
  /** 错误信息 */
  error?: string;
}

/** MCP 分发响应 */
export interface MCPDistributeResponse {
  /** 分发结果列表 */
  results: MCPDistributeResult[];
}