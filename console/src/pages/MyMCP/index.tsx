/**
 * 我的 MCP 页面 - Master-Detail 布局
 */
import { useEffect, useState } from "react";
import {
  Input,
  Button,
  List,
  Typography,
  Tag,
  Spin,
  Empty,
  Popconfirm,
  message,
  Space,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  ApiOutlined,
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  RocketOutlined,
} from "@ant-design/icons";
import { useMyMCP } from "./useMyMCP";
import { MCPDetailPanel } from "./MCPDetailPanel";
import { MCPFormModal } from "./MCPFormModal";
import { PublishMCPModal } from "./PublishMCPModal";
import { useIframeStore } from "../../stores/iframeStore";
import { getUserId } from "../../utils/identity";
import { DEFAULT_SOURCE_ID } from "../../constants/identity";
import type { MyMCPListItem } from "../../api/types";

const { Text } = Typography;

export default function MyMCPPage() {
  const sourceId = useIframeStore((state) => state.source) || DEFAULT_SOURCE_ID;
  const userId = getUserId();
  const userName = useIframeStore((state) => state.clawName) || "Unknown";
  const isManager = useIframeStore((state) => state.manager);

  const {
    mcpList,
    selectedMCP,
    loading,
    detailLoading,
    refreshList,
    fetchDetail,
    deleteMCP,
    toggleMCP,
    setSelectedMCP,
  } = useMyMCP();

  const [searchQuery, setSearchQuery] = useState("");
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [editingClientKey, setEditingClientKey] = useState<string | null>(null);
  const [selectedForPublish, setSelectedForPublish] = useState<string[]>([]);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  // 过滤列表
  const filteredList = mcpList.filter((mcp) => {
    const query = searchQuery.toLowerCase();
    return mcp.name.toLowerCase().includes(query);
  });

  // 点击列表项
  const handleItemClick = (item: MyMCPListItem) => {
    fetchDetail(item.client_key);
    setSelectedForPublish([]);
  };

  // 编辑 MCP
  const handleEdit = (clientKey: string) => {
    setEditingClientKey(clientKey);
    setFormModalOpen(true);
  };

  // 删除 MCP
  const handleDelete = async (clientKey: string) => {
    try {
      await deleteMCP(clientKey);
      message.success("删除成功");
    } catch {
      message.error("删除失败");
    }
  };

  // 启停 MCP
  const handleToggle = async (clientKey: string) => {
    try {
      const result = await toggleMCP(clientKey);
      message.success(result.enabled ? "已启用" : "已禁用");
    } catch {
      message.error("操作失败");
    }
  };

  // 判断是否为市场分发的 MCP
  const isDistributed = (item: MyMCPListItem) => {
    return item.source && item.source.startsWith("marketplace:");
  };

  return (
    <div style={{ display: "flex", height: "100%" }}>
      {/* 左侧列表 */}
      <div style={{ width: 360, borderRight: "1px solid #f0f0f0", display: "flex", flexDirection: "column" }}>
        {/* 搜索栏 */}
        <div style={{ padding: 16, borderBottom: "1px solid #f0f0f0" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ApiOutlined style={{ fontSize: 18 }} />
              <Text strong style={{ fontSize: 16 }}>我的 MCP</Text>
            </div>
            <Space>
              {isManager && selectedForPublish.length > 0 && (
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  size="small"
                  onClick={() => setPublishModalOpen(true)}
                >
                  发布 ({selectedForPublish.length})
                </Button>
              )}
              <Button icon={<PlusOutlined />} size="small" onClick={() => { setEditingClientKey(null); setFormModalOpen(true); }}>
                创建
              </Button>
            </Space>
          </div>
          <Input
            placeholder="搜索 MCP 名称"
            prefix={<SearchOutlined />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            allowClear
            size="small"
          />
        </div>

        {/* 列表 */}
        <div style={{ flex: 1, overflow: "auto" }}>
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 100 }}>
              <Spin />
            </div>
          ) : filteredList.length === 0 ? (
            <Empty description={searchQuery ? "未找到匹配的 MCP" : "暂无 MCP"} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={filteredList}
              renderItem={(item) => {
                const isSelected = selectedMCP?.client_key === item.client_key;
                const isPubSelected = selectedForPublish.includes(item.client_key);
                const distributed = isDistributed(item);

                return (
                  <List.Item
                    style={{
                      padding: "12px 16px",
                      cursor: "pointer",
                      backgroundColor: isSelected ? "#e6f7ff" : "transparent",
                      borderBottom: "1px solid #f0f0f0",
                    }}
                    onClick={() => handleItemClick(item)}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <Text strong style={{ fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {item.name}
                          </Text>
                          <Tag color={item.enabled ? "green" : "default"} style={{ margin: 0 }}>
                            {item.enabled ? "启用" : "禁用"}
                          </Tag>
                          {distributed && (
                            <Tag color="purple" style={{ margin: 0 }}>市场分发</Tag>
                          )}
                        </div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {item.client_key}
                        </Text>
                      </div>
                      <Space size={4}>
                        {isManager && !distributed && (
                          <CheckboxLike
                            checked={isPubSelected}
                            onChange={(checked) => {
                              if (checked) {
                                setSelectedForPublish([...selectedForPublish, item.client_key]);
                              } else {
                                setSelectedForPublish(selectedForPublish.filter(k => k !== item.client_key));
                              }
                            }}
                          />
                        )}
                        <Tooltip title={item.enabled ? "禁用" : "启用"}>
                          <Button
                            type="text"
                            size="small"
                            icon={item.enabled ? <CloseOutlined /> : <CheckOutlined />}
                            onClick={(e) => { e.stopPropagation(); handleToggle(item.client_key); }}
                          />
                        </Tooltip>
                        {!distributed && (
                          <Tooltip title="编辑">
                            <Button
                              type="text"
                              size="small"
                              onClick={(e) => { e.stopPropagation(); handleEdit(item.client_key); }}
                            >
                              编辑
                            </Button>
                          </Tooltip>
                        )}
                        <Popconfirm
                          title="确认删除此 MCP？"
                          onConfirm={(e) => { e?.stopPropagation(); handleDelete(item.client_key); }}
                          onCancel={(e) => e?.stopPropagation()}
                        >
                          <Tooltip title="删除">
                            <Button
                              type="text"
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={(e) => e.stopPropagation()}
                            />
                          </Tooltip>
                        </Popconfirm>
                      </Space>
                    </div>
                  </List.Item>
                );
              }}
            />
          )}
        </div>
      </div>

      {/* 右侧详情面板 */}
      <div style={{ flex: 1, overflow: "auto", backgroundColor: "#fafafa" }}>
        {detailLoading ? (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
            <Spin />
          </div>
        ) : selectedMCP ? (
          <MCPDetailPanel
            mcp={selectedMCP}
            onEdit={() => handleEdit(selectedMCP.client_key)}
            onToggle={() => handleToggle(selectedMCP.client_key)}
            onDelete={() => handleDelete(selectedMCP.client_key)}
            isManager={isManager}
            distributed={isDistributed(selectedMCP)}
          />
        ) : (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
            <Empty description="请选择 MCP 查看详情" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </div>
        )}
      </div>

      {/* 创建/编辑弹窗 */}
      <MCPFormModal
        open={formModalOpen}
        clientKey={editingClientKey}
        initialData={editingClientKey ? selectedMCP : null}
        onClose={() => { setFormModalOpen(false); setEditingClientKey(null); }}
        onSuccess={() => {
          setFormModalOpen(false);
          setEditingClientKey(null);
          refreshList();
        }}
      />

      {/* 发布到市场弹窗 */}
      {isManager && (
        <PublishMCPModal
          open={publishModalOpen}
          sourceId={sourceId}
          userId={userId}
          userName={userName}
          selectedKeys={selectedForPublish}
          onClose={() => { setPublishModalOpen(false); setSelectedForPublish([]); }}
          onSuccess={() => {
            setPublishModalOpen(false);
            setSelectedForPublish([]);
            refreshList();
          }}
        />
      )}
    </div>
  );
}

/** 模拟 Checkbox 的选择按钮 */
function CheckboxLike({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <div
      onClick={(e) => { e.stopPropagation(); onChange(!checked); }}
      style={{
        width: 16,
        height: 16,
        borderRadius: 2,
        border: `1px solid ${checked ? "#1890ff" : "#d9d9d9"}`,
        backgroundColor: checked ? "#1890ff" : "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        transition: "all 0.2s",
      }}
    >
      {checked && <CheckOutlined style={{ color: "#fff", fontSize: 10 }} />}
    </div>
  );
}