/**
 * 市场 MCP API（调用市场服务）
 */
import { request } from "../request";
import { buildAuthHeaders } from "../authHeaders";
import type {
  MarketMCPItem,
  MarketMCPDetail,
  MCPUploadRequest,
  MCPDistributeRequest,
  MCPDistributeResponse,
  MCPTestResult,
} from "../types";

function mergeHeaders(extra?: Record<string, string>): RequestInit {
  const base = buildAuthHeaders();
  const merged: Record<string, string> = { ...base, ...(extra || {}) };
  return { headers: new Headers(merged) };
}

export const marketMcpApi = {
  /**
   * 获取市场 MCP 列表
   */
  listMarketMCP: async (
    sourceId: string,
    bbkId: string,
    categoryId?: number
  ): Promise<MarketMCPItem[]> => {
    let url = "/market/mcp";
    const params = new URLSearchParams();
    if (categoryId !== undefined) {
      params.append("category_id", String(categoryId));
    }
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    const opts = mergeHeaders({
      "X-Source-Id": sourceId,
      "X-Bbk-Id": bbkId,
    });
    return request<MarketMCPItem[]>(url, opts);
  },

  /**
   * 获取市场 MCP 详情
   */
  getMarketMCPDetail: async (
    sourceId: string,
    itemId: string,
    bbkId: string
  ): Promise<MarketMCPDetail | null> => {
    const opts = mergeHeaders({
      "X-Source-Id": sourceId,
      "X-Bbk-Id": bbkId,
    });
    return request<MarketMCPDetail | null>(
      `/market/mcp/${itemId}`,
      opts
    );
  },

  /**
   * 上传 MCP 到市场（管理员）
   */
  uploadMCP: async (
    sourceId: string,
    userId: string,
    userName: string,
    data: MCPUploadRequest
  ): Promise<MarketMCPItem> => {
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
    return request<MarketMCPItem>("/market/mcp", opts);
  },

  /**
   * 分发 MCP 到用户（管理员）
   */
  distributeMCP: async (
    sourceId: string,
    itemId: string,
    userId: string,
    userName: string,
    data: MCPDistributeRequest
  ): Promise<MCPDistributeResponse> => {
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
    return request<MCPDistributeResponse>(
      `/market/mcp/${itemId}/distribute`,
      opts
    );
  },

  /**
   * 删除市场 MCP（管理员）
   */
  deleteMarketMCP: async (
    sourceId: string,
    itemId: string,
    userId: string,
    userName: string
  ): Promise<void> => {
    const opts: RequestInit = {
      method: "DELETE",
      headers: new Headers({
        "X-Source-Id": sourceId,
        "X-User-Id": userId,
        "X-User-Name": encodeURIComponent(userName),
        "X-Manager": "true",
      }),
    };
    return request<void>(`/market/mcp/${itemId}`, opts);
  },

  /**
   * 测试市场 MCP 连接（管理员）
   */
  testMarketMCP: async (
    sourceId: string,
    itemId: string,
    userId: string,
    userName: string
  ): Promise<MCPTestResult> => {
    const opts: RequestInit = {
      method: "POST",
      headers: new Headers({
        "X-Source-Id": sourceId,
        "X-User-Id": userId,
        "X-User-Name": encodeURIComponent(userName),
        "X-Manager": "true",
      }),
    };
    return request<MCPTestResult>(`/market/mcp/${itemId}/test`, opts);
  },
};