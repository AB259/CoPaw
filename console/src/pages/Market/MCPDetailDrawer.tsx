/**
 * 市场 MCP 详情抽屉
 */
import { useState } from "react";
import {
  Drawer,
  Descriptions,
  Typography,
  Tag,
  Button,
  Space,
  Table,
  Divider,
  Alert,
  Spin,
  message,
  Popconfirm,
} from "antd";
import {
  ApiOutlined,
  RocketOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { marketMcpApi } from "../../api/modules/marketMcp";
import type { MarketMCPDetail, MCPTestResult } from "../../api/types";

const { Title, Text } = Typography;

interface MCPDetailDrawerProps {
  open: boolean;
  mcp: MarketMCPDetail | null;
  sourceId: string;
  bbkId: string;
  userId: string;
  userName: string;
  isManager: boolean;
  onClose: () => void;
  onDistribute: () => void;
  onDelete: () => void;
  onRefresh: () => void;
}

export function MCPDetailDrawer({
  open,
  mcp,
  sourceId,
  userId,
  userName,
  isManager,
  onClose,
  onDistribute,
  onDelete,
}: MCPDetailDrawerProps) {
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<MCPTestResult | null>(null);

  if (!mcp) return null;

  const handleTest = async () => {
    setTestLoading(true);
    setTestResult(null);
    try {
      const result = await marketMcpApi.testMarketMCP(sourceId, mcp.item_id, userId, userName);
      setTestResult(result);
      if (result.success) {
        message.success(`连接成功，共 ${result.tools.length} 个工具`);
      } else {
        message.error(`连接失败: ${result.error}`);
      }
    } catch (err) {
      console.error("测试连接失败:", err);
      message.error("测试连接失败");
    } finally {
      setTestLoading(false);
    }
  };

  const transportLabel = {
    stdio: "STDIO",
    streamable_http: "HTTP",
    sse: "SSE",
  };

  const userStatsColumns = [
    { title: "用户 ID", dataIndex: "user_id", key: "user_id" },
    { title: "用户名", dataIndex: "user_name", key: "user_name" },
    {
      title: "调用次数",
      dataIndex: "call_count",
      key: "call_count",
      sorter: (a: { call_count: number }, b: { call_count: number }) => a.call_count - b.call_count,
    },
  ];

  const toolsColumns = [
    { title: "工具名称", dataIndex: "name", key: "name" },
    { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
  ];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={640}
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <ApiOutlined />
          <Title level={4} style={{ margin: 0 }}>{mcp.name}</Title>
        </div>
      }
      extra={
        isManager && (
          <Space>
            <Button icon={<ThunderboltOutlined />} loading={testLoading} onClick={handleTest}>
              测试连接
            </Button>
            <Button type="primary" icon={<RocketOutlined />} onClick={onDistribute}>
              分发
            </Button>
            <Popconfirm
              title="确认删除此 MCP？删除后不影响已分发用户"
              onConfirm={onDelete}
            >
              <Button danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        )
      }
    >
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="Client Key">{mcp.client_key}</Descriptions.Item>
        <Descriptions.Item label="描述">{mcp.description || "暂无"}</Descriptions.Item>
        <Descriptions.Item label="创建人">{mcp.creator_name}</Descriptions.Item>
        <Descriptions.Item label="调用次数">{mcp.call_count}</Descriptions.Item>
        <Descriptions.Item label="用户量">{mcp.user_count}</Descriptions.Item>
      </Descriptions>

      <Divider />

      {/* 连接配置 */}
      <Title level={5} style={{ marginBottom: 12 }}>
        连接配置
      </Title>
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="传输类型">
          <Tag>{transportLabel[mcp.config.transport]}</Tag>
        </Descriptions.Item>
        {mcp.config.transport === "stdio" ? (
          <>
            <Descriptions.Item label="命令">{mcp.config.command || "-"}</Descriptions.Item>
            <Descriptions.Item label="参数" span={2}>
              {mcp.config.args?.length > 0 ? (
                <Text code>{mcp.config.args.join(" ")}</Text>
              ) : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="环境变量" span={2}>
              {mcp.config.env && Object.keys(mcp.config.env).length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {Object.entries(mcp.config.env).map(([key, value]) => (
                    <div key={key}>
                      <Text code>{key}</Text>: <Text type="secondary">{value}</Text>
                    </div>
                  ))}
                </div>
              ) : "-"}
            </Descriptions.Item>
          </>
        ) : (
          <>
            <Descriptions.Item label="URL" span={2}>{mcp.config.url || "-"}</Descriptions.Item>
            <Descriptions.Item label="Headers" span={2}>
              {mcp.config.headers && Object.keys(mcp.config.headers).length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {Object.entries(mcp.config.headers).map(([key, value]) => (
                    <div key={key}>
                      <Text code>{key}</Text>: <Text type="secondary">{value}</Text>
                    </div>
                  ))}
                </div>
              ) : "-"}
            </Descriptions.Item>
          </>
        )}
      </Descriptions>

      {/* 测试结果 */}
      {testResult && (
        <div style={{ marginTop: 16 }}>
          <Title level={5} style={{ marginBottom: 12 }}>连接测试结果</Title>
          {testResult.success ? (
            <>
              <Alert type="success" message={`连接成功，共 ${testResult.tools.length} 个可用工具`} style={{ marginBottom: 12 }} />
              {testResult.tools.length > 0 && (
                <Table
                  dataSource={testResult.tools}
                  columns={toolsColumns}
                  rowKey="name"
                  pagination={false}
                  size="small"
                />
              )}
            </>
          ) : (
            <Alert type="error" message={testResult.error || "连接失败"} />
          )}
        </div>
      )}

      {/* 用户统计 */}
      <Divider />
      <Title level={5} style={{ marginBottom: 12 }}>
        调用用户明细
      </Title>
      <Table
        dataSource={mcp.user_stats}
        columns={userStatsColumns}
        rowKey="user_id"
        pagination={{ pageSize: 10 }}
        size="small"
      />
    </Drawer>
  );
}