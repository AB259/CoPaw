/**
 * MCP 详情面板
 */
import { useState } from "react";
import {
  Card,
  Descriptions,
  Typography,
  Tag,
  Button,
  Space,
  Spin,
  Alert,
  Table,
  Divider,
  Tooltip,
  Popconfirm,
  message,
} from "antd";
import {
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useMyMCP } from "./useMyMCP";
import type { MyMCPDetail } from "../../api/types";

const { Title, Text } = Typography;

interface MCPDetailPanelProps {
  mcp: MyMCPDetail;
  onEdit: () => void;
  onToggle: () => void;
  onDelete: () => void;
  isManager: boolean;
  distributed: boolean;
}

export function MCPDetailPanel({ mcp, onEdit, onToggle, onDelete, isManager, distributed }: MCPDetailPanelProps) {
  const { testConnection, testResult, testLoading, clearTestResult } = useMyMCP();
  const [testing, setTesting] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await testConnection(mcp.client_key);
      if (result.success) {
        message.success(`连接成功，共 ${result.tools.length} 个工具`);
      } else {
        message.error(`连接失败: ${result.error}`);
      }
    } finally {
      setTesting(false);
    }
  };

  const transportLabel = {
    stdio: "STDIO",
    streamable_http: "HTTP",
    sse: "SSE",
  };

  const toolsColumns = [
    {
      title: "工具名称",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      {/* 标题区域 */}
      <Card styles={{ body: { padding: 16 } }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>{mcp.name}</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>{mcp.client_key}</Text>
          </div>
          <Space>
            <Tag color={mcp.enabled ? "green" : "default"}>
              {mcp.enabled ? "启用" : "禁用"}
            </Tag>
            {distributed && (
              <Tag color="purple">市场分发</Tag>
            )}
          </Space>
        </div>
        <Divider style={{ margin: "16px 0" }} />
        <div style={{ display: "flex", gap: 12 }}>
          <Button
            icon={<ReloadOutlined />}
            loading={testing}
            onClick={handleTest}
          >
            测试连接
          </Button>
          {!distributed && (
            <Button icon={<EditOutlined />} onClick={onEdit}>
              编辑配置
            </Button>
          )}
          <Button
            icon={mcp.enabled ? <CloseOutlined /> : <CheckOutlined />}
            onClick={onToggle}
          >
            {mcp.enabled ? "禁用" : "启用"}
          </Button>
          <Popconfirm
            title="确认删除此 MCP？"
            onConfirm={onDelete}
          >
            <Button danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </div>
      </Card>

      {/* 连接测试结果 */}
      {testResult && (
        <Card styles={{ body: { padding: 16 } }} style={{ marginTop: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <Title level={5} style={{ margin: 0 }}>
              <ApiOutlined style={{ marginRight: 8 }} />
              连接测试结果
            </Title>
            <Button size="small" onClick={clearTestResult}>清除</Button>
          </div>
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
        </Card>
      )}

      {/* 基本信息 */}
      <Card styles={{ body: { padding: 16 } }} style={{ marginTop: 16 }} title={<Title level={5} style={{ margin: 0 }}>基本信息</Title>}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="描述">{mcp.description || "暂无描述"}</Descriptions.Item>
          <Descriptions.Item label="传输类型">
            <Tag>{transportLabel[mcp.transport]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{mcp.created_at || "-"}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{mcp.updated_at || "-"}</Descriptions.Item>
          {distributed && (
            <>
              <Descriptions.Item label="来源">{mcp.source}</Descriptions.Item>
              <Descriptions.Item label="分发者">{mcp.distributed_by || "-"}</Descriptions.Item>
            </>
          )}
        </Descriptions>
      </Card>

      {/* 连接配置 */}
      <Card styles={{ body: { padding: 16 } }} style={{ marginTop: 16 }} title={<Title level={5} style={{ margin: 0 }}>连接配置</Title>}>
        {mcp.transport === "stdio" ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="命令">{mcp.command || "-"}</Descriptions.Item>
            <Descriptions.Item label="参数">
              {mcp.args?.length > 0 ? (
                <Text code>{mcp.args.join(" ")}</Text>
              ) : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="环境变量">
              {mcp.env && Object.keys(mcp.env).length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {Object.entries(mcp.env).map(([key, value]) => (
                    <div key={key}>
                      <Text code>{key}</Text>: <Text type="secondary">{value}</Text>
                    </div>
                  ))}
                </div>
              ) : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="工作目录">{mcp.cwd || "-"}</Descriptions.Item>
          </Descriptions>
        ) : (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="URL">{mcp.url || "-"}</Descriptions.Item>
            <Descriptions.Item label="Headers">
              {mcp.headers && Object.keys(mcp.headers).length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {Object.entries(mcp.headers).map(([key, value]) => (
                    <div key={key}>
                      <Text code>{key}</Text>: <Text type="secondary">{value}</Text>
                    </div>
                  ))}
                </div>
              ) : "-"}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* 分发来源信息 */}
      {distributed && mcp.market_client_key && (
        <Card styles={{ body: { padding: 16 } }} style={{ marginTop: 16 }} title={<Title level={5} style={{ margin: 0 }}>分发来源</Title>}>
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="市场 client_key">{mcp.market_client_key}</Descriptions.Item>
            <Descriptions.Item label="分发者">{mcp.distributed_by || "-"}</Descriptions.Item>
          </Descriptions>
          <Alert
            type="info"
            message="此 MCP 由市场分发，连接配置不可修改。可以启停、测试连接或删除。"
            style={{ marginTop: 12 }}
            showIcon
          />
        </Card>
      )}
    </div>
  );
}