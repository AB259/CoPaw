/**
 * 市场 MCP 卡片
 */
import { Card, Tag, Typography } from "antd";
import { Users, PhoneCall } from "lucide-react";
import type { MarketMCPItem } from "../../api/types";

const { Text } = Typography;

interface MCPCardProps {
  mcp: MarketMCPItem;
  onClick: () => void;
}

export function MCPCard({ mcp, onClick }: MCPCardProps) {
  return (
    <Card
      hoverable
      onClick={onClick}
      styles={{
        body: { padding: 16 },
      }}
    >
      <div style={{ marginBottom: 8 }}>
        <Text strong style={{ fontSize: 16 }}>
          {mcp.name}
        </Text>
      </div>
      <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        {mcp.description || "暂无描述"}
      </Text>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {mcp.client_key}
        </Text>
        <div style={{ display: "flex", gap: 12 }}>
          <div
            style={{
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              borderRadius: 4,
              padding: "4px 8px",
              color: "#fff",
              fontSize: 12,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <PhoneCall size={12} />
            {mcp.call_count}
          </div>
          <div
            style={{
              background: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
              borderRadius: 4,
              padding: "4px 8px",
              color: "#fff",
              fontSize: 12,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Users size={12} />
            {mcp.user_count}
          </div>
        </div>
      </div>
    </Card>
  );
}