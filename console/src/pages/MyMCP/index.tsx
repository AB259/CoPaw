/**
 * 我的 MCP 页面 - 参考 CmbCoworkAgent UI 设计
 */
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import {
  Input,
  Button,
  Typography,
  Tag,
  Spin,
  Empty,
  Popconfirm,
  message,
  Switch,
  Descriptions,
  Divider,
  Alert,
  Card,
} from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  ApiOutlined,
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  EditOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";
import { Plug, Power, Trash2, Database, X, Search } from "lucide-react";
import { useMyMCP } from "./useMyMCP";
import { MCPFormModal } from "./MCPFormModal";
import { PublishMCPModal } from "./PublishMCPModal";
import { useIframeStore } from "../../stores/iframeStore";
import { getUserId } from "../../utils/identity";
import { DEFAULT_SOURCE_ID } from "../../constants/identity";
import type { MyMCPDetail, MyMCPListItem } from "../../api/types";

const { Text, Title } = Typography;

/** 获取 MCP 连接摘要 */
function getConnectorSummary(mcp: MyMCPDetail): string {
  if (mcp.transport === "stdio") {
    return [mcp.command ?? "", ...(mcp.args ?? [])].filter(Boolean).join(" ");
  }
  return mcp.url ?? "";
}

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
    testResult,
    testLoading,
    refreshList,
    fetchDetail,
    deleteMCP,
    toggleMCP,
    createMCP,
    updateMCP,
    testConnection,
    clearTestResult,
    setSelectedMCP,
  } = useMyMCP();

  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [editingClientKey, setEditingClientKey] = useState<string | null>(null);
  const [selectedForPublish, setSelectedForPublish] = useState<string[]>([]);
  const [testing, setTesting] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // 搜索防抖
  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value);
    clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => setDebouncedQuery(value), 200);
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  // 过滤列表
  const filteredList = useMemo(() => {
    const q = debouncedQuery.trim().toLowerCase();
    if (!q) return mcpList;
    return mcpList.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.client_key.toLowerCase().includes(q)
    );
  }, [mcpList, debouncedQuery]);

  // 点击列表项
  const handleItemClick = useCallback((item: MyMCPListItem) => {
    fetchDetail(item.client_key);
    setSelectedForPublish([]);
    clearTestResult();
  }, [fetchDetail, clearTestResult]);

  // 编辑 MCP
  const handleEdit = useCallback((clientKey: string) => {
    setEditingClientKey(clientKey);
    setFormModalOpen(true);
  }, []);

  // 删除 MCP
  const handleDelete = useCallback(async (mcp: MyMCPDetail) => {
    try {
      await deleteMCP(mcp.client_key);
      message.success("删除成功");
    } catch {
      message.error("删除失败");
    }
  }, [deleteMCP]);

  // 启停 MCP
  const handleToggle = useCallback(async (clientKey: string, enabled: boolean) => {
    try {
      await toggleMCP(clientKey);
      message.success(enabled ? "已启用" : "已禁用");
    } catch {
      message.error("操作失败");
    }
  }, [toggleMCP]);

  // 测试连接
  const handleTest = useCallback(async () => {
    if (!selectedMCP) return;
    setTesting(true);
    try {
      await testConnection(selectedMCP.client_key);
    } finally {
      setTesting(false);
    }
  }, [selectedMCP, testConnection]);

  // 判断是否为市场分发的 MCP
  const isDistributed = useCallback((item: MyMCPListItem | MyMCPDetail) => {
    return item.source && item.source.startsWith("marketplace:");
  }, []);

  // 清除搜索
  const clearSearch = useCallback(() => {
    setSearchQuery("");
    setDebouncedQuery("");
  }, []);

  // 切换发布选择
  const togglePublishSelection = useCallback((clientKey: string, checked: boolean) => {
    if (checked) {
      setSelectedForPublish([...selectedForPublish, clientKey]);
    } else {
      setSelectedForPublish(selectedForPublish.filter(k => k !== clientKey));
    }
  }, [selectedForPublish]);

  return (
    <div className="flex h-full bg-[#fafafa]">
      {/* 左侧列表 */}
      <div className="w-[330px] shrink-0 border-r border-[#f0f0f0] flex flex-col bg-white">
        {/* 头部 */}
        <div className="p-3 border-b border-[#f0f0f0] space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <div className="size-7 rounded-xl bg-[#e6f7ff] border border-[#91d5ff] flex items-center justify-center">
                <Plug className="size-3.5 text-[#1890ff]" />
              </div>
              <h2 className="text-base font-bold text-[#262626]">MCP 连接器</h2>
            </div>
            <div className="flex items-center gap-1.5">
              {isManager && selectedForPublish.length > 0 && (
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  size="small"
                  className="h-7 text-xs"
                  onClick={() => setPublishModalOpen(true)}
                >
                  发布 ({selectedForPublish.length})
                </Button>
              )}
              <Button
                icon={<PlusOutlined />}
                size="small"
                className="h-7 w-7"
                onClick={() => { setEditingClientKey(null); setFormModalOpen(true); }}
              />
            </div>
          </div>

          {/* 搜索框 */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-[#bfbfbf] pointer-events-none" />
            <Input
              placeholder="搜索"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="h-7 pl-8 pr-7 text-xs bg-white border-[#d9d9d9] text-[#262626] placeholder:text-[#bfbfbf] rounded-md"
            />
            {searchQuery && (
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-[#bfbfbf] hover:text-[#595959] p-0.5 rounded cursor-pointer"
                onClick={clearSearch}
              >
                <X className="size-3" />
              </button>
            )}
          </div>
        </div>

        {/* 列表 */}
        <div className="flex-1 overflow-auto p-2 space-y-2">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-[#595959]">
              <Spin />
            </div>
          ) : filteredList.length === 0 ? (
            <p className="text-xs text-[#595959] px-1 py-2 text-center">
              {mcpList.length === 0 ? "暂无连接器，点击 + 添加" : "没有匹配的连接器"}
            </p>
          ) : (
            filteredList.map((item) => {
              const isSelected = selectedMCP?.client_key === item.client_key;
              const isPubSelected = selectedForPublish.includes(item.client_key);
              const distributed = isDistributed(item);

              return (
                <button
                  key={item.client_key}
                  className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-md border text-left transition-colors cursor-pointer ${
                    isSelected
                      ? "bg-[#e6f7ff] border-[#91d5ff]"
                      : "border-[#f0f0f0] hover:bg-[#fafafa]"
                  }`}
                  onClick={() => handleItemClick(item)}
                >
                  <Plug className={`size-3.5 shrink-0 ${item.enabled ? "text-[#1890ff]" : "text-[#8c8c8c]"}`} />
                  <span className={`text-sm truncate flex-1 ${!item.enabled && "text-[#8c8c8c]"}`}>
                    {item.name}
                  </span>
                  {distributed && (
                    <Tag color="purple" className="m-0 text-[10px]">分发</Tag>
                  )}
                  {!item.enabled && (
                    <Tag className="m-0 text-[10px] bg-[#fafafa] border-[#d9d9d9] text-[#8c8c8c]">禁用</Tag>
                  )}
                  {isManager && !distributed && (
                    <div
                      className="size-4 shrink-0 rounded border cursor-pointer flex items-center justify-center transition-colors"
                      style={{
                        borderColor: isPubSelected ? "#1890ff" : "#d9d9d9",
                        backgroundColor: isPubSelected ? "#1890ff" : "#fff",
                      }}
                      onClick={(e) => { e.stopPropagation(); togglePublishSelection(item.client_key, !isPubSelected); }}
                    >
                      {isPubSelected && <CheckOutlined className="text-white text-[10px]" />}
                    </div>
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* 右侧详情面板 */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#fafafa]">
        {detailLoading ? (
          <div className="flex items-center justify-center h-full">
            <Spin />
          </div>
        ) : selectedMCP ? (
          <>
            {/* 详情头部 */}
            <div className="p-4 border-b border-[#f0f0f0] flex items-start justify-between gap-3 bg-white">
              <div className="min-w-0 flex-1">
                <h2 className="text-base font-semibold truncate text-[#262626]">{selectedMCP.name}</h2>
                <p className="text-xs text-[#8c8c8c] mt-0.5 truncate">{getConnectorSummary(selectedMCP)}</p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {!isDistributed(selectedMCP) && (
                  <Button
                    className="h-7 text-xs text-[#595959] border-[#d9d9d9] bg-white"
                    onClick={() => handleEdit(selectedMCP.client_key)}
                  >
                    编辑
                  </Button>
                )}
                <Popconfirm
                  title={`确定要删除连接器「${selectedMCP.name}」吗？`}
                  onConfirm={() => handleDelete(selectedMCP)}
                >
                  <Button
                    danger
                    className="h-7 text-xs"
                    icon={<DeleteOutlined />}
                  >
                    删除
                  </Button>
                </Popconfirm>
                <Button
                  type={selectedMCP.enabled ? "primary" : "default"}
                  className="h-7 text-xs"
                  icon={<Power className="size-3 mr-1" />}
                  onClick={() => handleToggle(selectedMCP.client_key, !selectedMCP.enabled)}
                >
                  {selectedMCP.enabled ? "已启用" : "已禁用"}
                </Button>
              </div>
            </div>

            {/* 测试连接 */}
            <div className="px-4 py-3 border-b border-[#f0f0f0] bg-white">
              <Button
                className="h-7 text-xs border-[#d9d9d9] bg-white"
                icon={<ThunderboltOutlined />}
                loading={testing}
                onClick={handleTest}
              >
                {testing ? "测试中..." : "测试连接"}
              </Button>
              {testResult && (
                <div className={`mt-2 text-xs ${testResult.success ? "text-[#52c41a]" : "text-[#ff4d4f]"}`}>
                  {testResult.success ? (
                    <div>
                      <p className="font-medium">连接成功，共 {testResult.tools?.length ?? 0} 个工具：</p>
                      {testResult.tools && testResult.tools.length > 0 && (
                        <ul className="mt-1 list-disc list-inside space-y-0.5 text-[#8c8c8c]">
                          {testResult.tools.slice(0, 10).map((t) => (
                            <li key={t.name}>{t.name}</li>
                          ))}
                          {testResult.tools.length > 10 && (
                            <li className="text-[#8c8c8c]">... 等 {testResult.tools.length - 10} 个</li>
                          )}
                        </ul>
                      )}
                    </div>
                  ) : (
                    <p>{testResult.error}</p>
                  )}
                </div>
              )}
            </div>

            {/* 懒加载开关 */}
            <div className="px-4 py-3 border-b border-[#f0f0f0] bg-white">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium text-[#262626]">懒加载</p>
                  <p className="text-xs text-[#8c8c8c]">
                    {selectedMCP.lazy_load
                      ? "工具通过 search_tool 搜索后按需加载"
                      : "所有工具直接加载到上下文中"}
                  </p>
                </div>
                <Button
                  type={selectedMCP.lazy_load ? "primary" : "default"}
                  className="h-7 text-xs"
                  icon={<DatabaseOutlined />}
                >
                  {selectedMCP.lazy_load ? "已开启" : "已关闭"}
                </Button>
              </div>
            </div>

            {/* 安全提示 */}
            <div className="px-4 py-3 border-b border-[#f0f0f0] bg-white">
              <p className="text-xs text-[#8c8c8c]">
                MCP 连接器可访问你配置的数据与工具。请仅添加你信任的服务器。
              </p>
            </div>

            {/* 基本信息 */}
            <div className="px-4 py-3 border-b border-[#f0f0f0] bg-white">
              <Title level={5} className="text-sm font-medium mb-3 text-[#262626]">基本信息</Title>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="Client Key">{selectedMCP.client_key}</Descriptions.Item>
                <Descriptions.Item label="描述">{selectedMCP.description || "暂无"}</Descriptions.Item>
                <Descriptions.Item label="传输类型">
                  <Tag>{selectedMCP.transport === "stdio" ? "STDIO" : selectedMCP.transport === "streamable_http" ? "HTTP" : "SSE"}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="来源">
                  {isDistributed(selectedMCP) ? (
                    <Tag color="purple">市场分发</Tag>
                  ) : (
                    <Tag color="green">本地创建</Tag>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">{selectedMCP.created_at || "-"}</Descriptions.Item>
                <Descriptions.Item label="更新时间">{selectedMCP.updated_at || "-"}</Descriptions.Item>
              </Descriptions>
            </div>

            {/* 连接配置 */}
            <div className="px-4 py-3 bg-white">
              <Title level={5} className="text-sm font-medium mb-3 text-[#262626]">连接配置</Title>
              {selectedMCP.transport === "stdio" ? (
                <Descriptions column={1} size="small" bordered>
                  <Descriptions.Item label="命令">{selectedMCP.command || "-"}</Descriptions.Item>
                  <Descriptions.Item label="参数">
                    {selectedMCP.args?.length > 0 ? (
                      <Text code>{selectedMCP.args.join(" ")}</Text>
                    ) : "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="环境变量">
                    {selectedMCP.env && Object.keys(selectedMCP.env).length > 0 ? (
                      <div className="space-y-1">
                        {Object.entries(selectedMCP.env).map(([key, value]) => (
                          <div key={key}>
                            <Text code>{key}</Text>: <Text type="secondary">{value}</Text>
                          </div>
                        ))}
                      </div>
                    ) : "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="工作目录">{selectedMCP.cwd || "-"}</Descriptions.Item>
                </Descriptions>
              ) : (
                <Descriptions column={1} size="small" bordered>
                  <Descriptions.Item label="URL">{selectedMCP.url || "-"}</Descriptions.Item>
                  <Descriptions.Item label="Headers">
                    {selectedMCP.headers && Object.keys(selectedMCP.headers).length > 0 ? (
                      <div className="space-y-1">
                        {Object.entries(selectedMCP.headers).map(([key, value]) => (
                          <div key={key}>
                            <Text code>{key}</Text>: <Text type="secondary">{value}</Text>
                          </div>
                        ))}
                      </div>
                    ) : "-"}
                  </Descriptions.Item>
                </Descriptions>
              )}

              {isDistributed(selectedMCP) && (
                <Alert
                  type="info"
                  message="此 MCP 由市场分发，连接配置不可修改"
                  className="mt-3"
                  showIcon
                />
              )}
            </div>
          </>
        ) : (
          // 空状态
          <div className="flex-1 flex items-center justify-center p-8 bg-white">
            <div className="max-w-md space-y-6 text-center">
              <div className="size-14 rounded-2xl bg-[#e6f7ff] border border-[#91d5ff] flex items-center justify-center mx-auto">
                <Plug className="size-7 text-[#1890ff]" />
              </div>
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-[#262626]">MCP 连接器</h3>
                <p className="text-sm text-[#8c8c8c] leading-relaxed">
                  MCP（Model Context Protocol）是一种开放协议，让 AI 能够连接远程工具服务器。
                  通过 MCP 连接器，AI 可以调用服务器提供的各种工具，大幅扩展能力边界。
                </p>
              </div>

              <div className="space-y-3">
                <div className="rounded-xl border border-[#f0f0f0] bg-[#fafafa] p-4 space-y-3">
                  <p className="text-sm font-medium text-[#262626]">什么是 MCP？</p>
                  <p className="text-[13px] text-[#8c8c8c] leading-relaxed">
                    MCP 服务器是一个远程服务，它向 AI 暴露一组工具。AI 在对话过程中会根据需要自动调用这些工具来获取信息或执行操作。
                    当前支持 <span className="font-medium text-[#262626]">STDIO</span>、
                    <span className="font-medium text-[#262626]">SSE</span> 和
                    <span className="font-medium text-[#262626]">Streamable HTTP</span> 三种传输协议。
                  </p>
                </div>

                <div className="rounded-xl border border-[#f0f0f0] bg-[#fafafa] p-4 space-y-3">
                  <p className="text-sm font-medium text-[#262626]">如何添加？</p>
                  <ul className="text-[13px] text-[#8c8c8c] space-y-2 leading-relaxed text-left">
                    <li className="flex gap-2">
                      <span className="text-[#8c8c8c] shrink-0">1.</span>
                      点击 <span className="font-medium text-[#262626]">+</span> 按钮，填写连接器名称和配置
                    </li>
                    <li className="flex gap-2">
                      <span className="text-[#8c8c8c] shrink-0">2.</span>
                      选择传输类型（STDIO / SSE / HTTP），配置命令或 URL
                    </li>
                    <li className="flex gap-2">
                      <span className="text-[#8c8c8c] shrink-0">3.</span>
                      保存后点击「测试连接」验证是否可用
                    </li>
                    <li className="flex gap-2">
                      <span className="text-[#8c8c8c] shrink-0">4.</span>
                      管理员可以将本地 MCP 发布到应用市场
                    </li>
                  </ul>
                </div>
              </div>
            </div>
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