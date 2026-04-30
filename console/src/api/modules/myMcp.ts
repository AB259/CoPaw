/**
 * 我的 MCP 管理 API
 */
import { request } from "../request";
import { buildAuthHeaders } from "../authHeaders";
import type {
  MyMCPListItem,
  MyMCPDetail,
  MyMCPCreateRequest,
  MyMCPUpdateRequest,
  PublishMCPRequest,
  PublishMCPResponse,
  MCPTestResult,
} from "../types";

function mergeHeaders(extra?: Record<string, string>): RequestInit {
  const base = buildAuthHeaders();
  const merged: Record<string, string> = { ...base, ...(extra || {}) };
  return { headers: new Headers(merged) };
}

export const myMcpApi = {
  /**
   * 获取我的 MCP 列表
   */
  listMyMCP: async (): Promise<MyMCPListItem[]> => {
    return request<MyMCPListItem[]>("/my-mcp");
  },

  /**
   * 获取单个 MCP 详情
   */
  getMyMCPDetail: async (clientKey: string): Promise<MyMCPDetail> => {
    return request<MyMCPDetail>(`/my-mcp/${encodeURIComponent(clientKey)}`);
  },

  /**
   * 创建新的 MCP
   */
  createMyMCP: async (data: MyMCPCreateRequest): Promise<MyMCPDetail> => {
    return request<MyMCPDetail>("/my-mcp", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /**
   * 更新 MCP 配置
   */
  updateMyMCP: async (
    clientKey: string,
    data: MyMCPUpdateRequest
  ): Promise<MyMCPDetail> => {
    return request<MyMCPDetail>(`/my-mcp/${encodeURIComponent(clientKey)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  /**
   * 删除 MCP
   */
  deleteMyMCP: async (clientKey: string): Promise<{ message: string }> => {
    return request<{ message: string }>(
      `/my-mcp/${encodeURIComponent(clientKey)}`,
      { method: "DELETE" }
    );
  },

  /**
   * 启用/禁用 MCP
   */
  toggleMyMCP: async (clientKey: string): Promise<MyMCPDetail> => {
    return request<MyMCPDetail>(
      `/my-mcp/${encodeURIComponent(clientKey)}/toggle`,
      { method: "PATCH" }
    );
  },

  /**
   * 测试 MCP 连接
   */
  testMyMCPConnection: async (clientKey: string): Promise<MCPTestResult> => {
    return request<MCPTestResult>(
      `/my-mcp/${encodeURIComponent(clientKey)}/test`,
      { method: "POST" }
    );
  },

  /**
   * 发布 MCP 到市场（管理员）
   */
  publishToMarket: async (
    sourceId: string,
    userId: string,
    userName: string,
    data: PublishMCPRequest
  ): Promise<PublishMCPResponse> => {
    const opts: RequestInit = {
      method: "POST",
      headers: new Headers({
        "Content-Type": "application/json",
        "X-Source-Id": sourceId,
        "X-User-Id": userId,
        "X-User-Name": encodeURIComponent(userName),
        "X-Manager": "true",
      }),
      body: JSON.stringify(data),
    };
    return request<PublishMCPResponse>("/my-mcp/publish", opts);
  },
};