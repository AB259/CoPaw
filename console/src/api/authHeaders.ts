import { getApiToken } from "./config";

// ==================== iframe 集成 (Kun He) ====================
// 引入 iframe 上下文存储，用于获取父窗口传递的用户信息
// 包括 userId (来自 sapId)、自定义 headers 等
import { getIframeContext } from "../stores/iframeStore";
// ==================== iframe 集成结束 ====================

/**
 * 构建认证和上下文相关的请求 headers
 *
 * 包含：
 * - Authorization: Bearer token
 * - X-Agent-Id: 当前选中的 agent
 * - X-User-Id: 用户 ID（来自 iframe userId，默认 "default"）
 * - X-Tenant-Id: 租户 ID（与 X-User-Id 保持一致）
 * - 自定义 headers（来自 iframe auth 数组）
 */
export function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  // 1. Token（优先级：localStorage > iframe context）
  const token = getApiToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  // 2. Agent ID（从 sessionStorage 读取当前选中的 agent）
  try {
    const agentStorage = sessionStorage.getItem("copaw-agent-storage");
    if (agentStorage) {
      const parsed = JSON.parse(agentStorage);
      const selectedAgent = parsed?.state?.selectedAgent;
      if (selectedAgent) {
        headers["X-Agent-Id"] = selectedAgent;
      }
    }
  } catch (error) {
    console.warn("Failed to get selected agent from storage:", error);
  }

  // 3. iframe 上下文参数（从父级 iframe 接收的参数）
  // ==================== iframe 集成 (Kun He) ====================
  // 用户 ID 和租户 ID：
  // - iframe 内嵌时：使用父窗口传递的 userId (来自 sapId)
  // - 非 iframe 模式：默认值为 "default"
  // X-Tenant-Id 与 X-User-Id 保持一致
  const iframeContext = getIframeContext();
  const userId = iframeContext.userId || "default";
  headers["X-User-Id"] = userId;
  headers["X-Tenant-Id"] = userId;

  // 自定义 headers 数组（父窗口通过 auth 字段传递）
  // 每项包含 headerName 和 headerValue
  if (iframeContext.authHeaders?.length) {
    for (const item of iframeContext.authHeaders) {
      if (item.headerName && item.headerValue !== undefined) {
        headers[item.headerName] = item.headerValue;
      }
    }
  }
  // ==================== iframe 集成结束 ====================

  return headers;
}
