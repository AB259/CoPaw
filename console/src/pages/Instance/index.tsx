import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Tabs, Card, Row, Col, Statistic, Table, Button, Space, Tag, Progress, Drawer, Form, Input, Select, Modal, message } from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SwapOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api from "../../api";
import type {
  InstanceWithUsage,
  UserAllocation,
  OperationLog,
  OverviewStats,
  AllocateUserRequest,
  SourceWithStats,
} from "../../api/modules/instance";

const { TabPane } = Tabs;

// 分行配置 - 硬编码
const BRANCHES = [
  { bbk_id: "head_office", bbk_name: "总行" },
  { bbk_id: "beijing", bbk_name: "北京分行" },
  { bbk_id: "shanghai", bbk_name: "上海分行" },
  { bbk_id: "guangzhou", bbk_name: "广州分行" },
  { bbk_id: "shenzhen", bbk_name: "深圳分行" },
  { bbk_id: "chengdu", bbk_name: "成都分行" },
  { bbk_id: "hangzhou", bbk_name: "杭州分行" },
  { bbk_id: "nanjing", bbk_name: "南京分行" },
];

function InstancePage() {
  const { t } = useTranslation();

  // Overview state
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // Sources state (用于下拉选择，不再单独管理)
  const [sources, setSources] = useState<SourceWithStats[]>([]);

  // Instances state
  const [instances, setInstances] = useState<InstanceWithUsage[]>([]);
  const [instancesLoading, setInstancesLoading] = useState(false);
  const [instanceFilter, setInstanceFilter] = useState<{ source_id?: string }>({});
  const [instanceDrawerOpen, setInstanceDrawerOpen] = useState(false);
  const [editingInstance, setEditingInstance] = useState<InstanceWithUsage | null>(null);
  const [instanceForm] = Form.useForm();

  // Allocations state
  const [allocations, setAllocations] = useState<UserAllocation[]>([]);
  const [allocationsTotal, setAllocationsTotal] = useState(0);
  const [allocationsLoading, setAllocationsLoading] = useState(false);
  const [allocationPage, setAllocationPage] = useState(1);
  const [allocationFilter, setAllocationFilter] = useState<{ user_id?: string; source_id?: string }>({});
  const [allocationDrawerOpen, setAllocationDrawerOpen] = useState(false);
  const [allocationForm] = Form.useForm();
  const [migrateDrawerOpen, setMigrateDrawerOpen] = useState(false);
  const [migratingAllocation, setMigratingAllocation] = useState<UserAllocation | null>(null);
  const [migrateForm] = Form.useForm();

  // Logs state
  const [logs, setLogs] = useState<OperationLog[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsPage, setLogsPage] = useState(1);
  const [logsFilter, setLogsFilter] = useState<{ action?: string; target_type?: string }>({});

  // 用于追踪筛选条件变化，避免 useEffect 重复触发
  const allocationFiltersRef = useRef<{ user_id?: string; source_id?: string }>({});
  const logsFiltersRef = useRef<{ action?: string; target_type?: string }>({});

  // Load overview
  const loadOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const data = await api.getOverview();
      setOverview(data);
    } catch (error) {
      console.error("Failed to load overview:", error);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  // Load sources
  const loadSources = useCallback(async () => {
    try {
      const data = await api.getSources();
      setSources(data.sources);
    } catch (error) {
      console.error("Failed to load sources:", error);
    }
  }, []);

  // Load instances
  const loadInstances = useCallback(async () => {
    setInstancesLoading(true);
    try {
      const data = await api.getInstances(instanceFilter);
      setInstances(data.instances);
    } catch (error) {
      console.error("Failed to load instances:", error);
    } finally {
      setInstancesLoading(false);
    }
  }, [instanceFilter]);

  // Load allocations
  const loadAllocations = useCallback(async () => {
    setAllocationsLoading(true);
    try {
      const data = await api.getAllocations({
        ...allocationFilter,
        page: allocationPage,
        page_size: 10,
      });
      setAllocations(data.allocations);
      setAllocationsTotal(data.total);
    } catch (error) {
      console.error("Failed to load allocations:", error);
    } finally {
      setAllocationsLoading(false);
    }
  }, [allocationFilter, allocationPage]);

  // Load logs
  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const data = await api.getLogs({
        ...logsFilter,
        page: logsPage,
        page_size: 10,
      });
      setLogs(data.logs);
      setLogsTotal(data.total);
    } catch (error) {
      console.error("Failed to load logs:", error);
    } finally {
      setLogsLoading(false);
    }
  }, [logsFilter, logsPage]);

  // Initial load
  useEffect(() => {
    loadOverview();
    loadSources();
    loadInstances();
    loadAllocations();
    loadLogs();
  }, [loadOverview, loadSources, loadInstances, loadAllocations, loadLogs]);

  // Reload instances when filter changes
  useEffect(() => {
    loadInstances();
  }, [instanceFilter, loadInstances]);

  // Reload allocations when filter or page changes
  useEffect(() => {
    // 检查筛选条件是否变化
    const filtersChanged =
      allocationFiltersRef.current.user_id !== allocationFilter.user_id ||
      allocationFiltersRef.current.source_id !== allocationFilter.source_id;

    // 更新 ref
    allocationFiltersRef.current = { ...allocationFilter };

    // 如果筛选条件变化且不是第一页，只重置页码不查询
    if (filtersChanged && allocationPage !== 1) {
      setAllocationPage(1);
      return;
    }

    loadAllocations();
  }, [allocationFilter, allocationPage, loadAllocations]);

  // Reload logs when filter or page changes
  useEffect(() => {
    // 检查筛选条件是否变化
    const filtersChanged =
      logsFiltersRef.current.action !== logsFilter.action ||
      logsFiltersRef.current.target_type !== logsFilter.target_type;

    // 更新 ref
    logsFiltersRef.current = { ...logsFilter };

    // 如果筛选条件变化且不是第一页，只重置页码不查询
    if (filtersChanged && logsPage !== 1) {
      setLogsPage(1);
      return;
    }

    loadLogs();
  }, [logsFilter, logsPage, loadLogs]);

  // Instance CRUD
  const handleCreateInstance = () => {
    setEditingInstance(null);
    instanceForm.resetFields();
    instanceForm.setFieldsValue({ max_users: 100 });
    setInstanceDrawerOpen(true);
  };

  const handleEditInstance = (record: InstanceWithUsage) => {
    setEditingInstance(record);
    instanceForm.setFieldsValue(record);
    setInstanceDrawerOpen(true);
  };

  const handleDeleteInstance = async (instanceId: string) => {
    Modal.confirm({
      title: t("instance.confirmDelete"),
      content: t("instance.confirmDeleteInstance"),
      okText: t("instance.delete"),
      okType: "danger",
      cancelText: t("common.cancel"),
      onOk: async () => {
        try {
          await api.deleteInstance(instanceId);
          message.success(t("instance.deleteSuccess"));
          loadInstances();
          loadOverview();
        } catch (error: unknown) {
          message.error((error as Error).message || t("instance.deleteFailed"));
        }
      },
    });
  };

  const handleSaveInstance = async (values: {
    instance_id: string;
    source_id: string;
    bbk_id?: string;
    instance_name: string;
    instance_url: string;
    max_users: number;
  }) => {
    try {
      if (editingInstance) {
        await api.updateInstance(editingInstance.instance_id, {
          instance_name: values.instance_name,
          instance_url: values.instance_url,
          max_users: values.max_users,
        });
        message.success(t("instance.updateSuccess"));
      } else {
        await api.createInstance(values);
        message.success(t("instance.createSuccess"));
      }
      setInstanceDrawerOpen(false);
      loadInstances();
      loadOverview();
    } catch (error: unknown) {
      message.error((error as Error).message || t("instance.saveFailed"));
    }
  };

  // Allocation operations
  const handleCreateAllocation = () => {
    allocationForm.resetFields();
    setAllocationDrawerOpen(true);
  };

  const handleSaveAllocation = async (values: AllocateUserRequest) => {
    try {
      const result = await api.allocateUser(values);
      if (result.success) {
        message.success(`${t("instance.allocateSuccess")}：${result.instance_url}`);
        setAllocationDrawerOpen(false);
        loadAllocations();
        loadInstances();
        loadOverview();
      } else {
        message.warning(result.message || t("instance.allocateFailed"));
      }
    } catch (error: unknown) {
      message.error((error as Error).message || t("instance.allocateFailed"));
    }
  };

  const handleMigrateAllocation = (record: UserAllocation) => {
    setMigratingAllocation(record);
    migrateForm.resetFields();
    migrateForm.setFieldsValue({
      user_id: record.user_id,
      source_id: record.source_id,
    });
    setMigrateDrawerOpen(true);
  };

  const handleSaveMigrate = async (values: { target_instance_id: string }) => {
    if (!migratingAllocation) return;
    try {
      const result = await api.migrateUser({
        user_id: migratingAllocation.user_id,
        source_id: migratingAllocation.source_id,
        target_instance_id: values.target_instance_id,
      });
      if (result.success) {
        message.success(t("instance.migrateSuccess"));
        setMigrateDrawerOpen(false);
        loadAllocations();
        loadInstances();
      } else {
        message.warning(result.message || t("instance.migrateFailed"));
      }
    } catch (error: unknown) {
      message.error((error as Error).message || t("instance.migrateFailed"));
    }
  };

  const handleDeleteAllocation = async (record: UserAllocation) => {
    Modal.confirm({
      title: t("instance.confirmDelete"),
      content: t("instance.confirmDeleteAllocation", { userId: record.user_id }),
      okText: t("instance.delete"),
      okType: "danger",
      cancelText: t("common.cancel"),
      onOk: async () => {
        try {
          await api.deleteAllocation(record.user_id, record.source_id);
          message.success(t("instance.deleteSuccess"));
          loadAllocations();
          loadInstances();
          loadOverview();
        } catch (error: unknown) {
          message.error((error as Error).message || t("instance.deleteFailed"));
        }
      },
    });
  };

  // Table columns
  const instanceColumns: ColumnsType<InstanceWithUsage> = [
    { title: t("instance.instanceId"), dataIndex: "instance_id", key: "instance_id", width: 120 },
    { title: t("instance.instanceName"), dataIndex: "instance_name", key: "instance_name" },
    { title: t("instance.source"), dataIndex: "source_name", key: "source_name", width: 100 },
    { title: t("instance.branch"), dataIndex: "bbk_name", key: "bbk_name", width: 100, render: (v) => v || "-" },
    {
      title: t("instance.userUsage"),
      key: "usage",
      width: 150,
      render: (_, record) => {
        const percent = record.usage_percent;
        let status: "success" | "normal" | "exception" = "success";
        if (percent >= 100) status = "exception";
        else if (percent >= 80) status = "normal";
        return (
          <Progress
            percent={Math.min(percent, 100)}
            status={status}
            format={() => `${record.current_users}/${record.max_users}`}
            size="small"
          />
        );
      },
    },
    {
      title: t("instance.status"),
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (v) => (
        <Tag color={v === "active" ? "green" : "default"}>{v === "active" ? t("instance.active") : t("instance.inactive")}</Tag>
      ),
    },
    {
      title: t("instance.warning"),
      key: "warning",
      width: 80,
      render: (_, record) => {
        if (record.warning_level === "critical") return <Tag color="red">{t("instance.critical")}</Tag>;
        if (record.warning_level === "warning") return <Tag color="orange">{t("instance.warning")}</Tag>;
        return <Tag color="green">{t("instance.normal")}</Tag>;
      },
    },
    {
      title: t("instance.action"),
      key: "action",
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditInstance(record)} />
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteInstance(record.instance_id)} />
        </Space>
      ),
    },
  ];

  const allocationColumns: ColumnsType<UserAllocation> = [
    { title: t("instance.userId"), dataIndex: "user_id", key: "user_id" },
    { title: t("instance.source"), dataIndex: "source_name", key: "source_name", width: 100 },
    { title: t("instance.instanceName"), dataIndex: "instance_name", key: "instance_name" },
    {
      title: t("instance.status"),
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (v) => (
        <Tag color={v === "active" ? "green" : "blue"}>{v === "active" ? t("instance.active") : t("instance.migrated")}</Tag>
      ),
    },
    {
      title: t("instance.allocatedAt"),
      dataIndex: "allocated_at",
      key: "allocated_at",
      width: 160,
      render: (v) => (v ? new Date(v).toLocaleString() : "-"),
    },
    {
      title: t("instance.action"),
      key: "action",
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<SwapOutlined />} onClick={() => handleMigrateAllocation(record)} />
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteAllocation(record)} />
        </Space>
      ),
    },
  ];

  const logColumns: ColumnsType<OperationLog> = [
    {
      title: t("instance.time"),
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: (v) => (v ? new Date(v).toLocaleString() : "-"),
    },
    { title: t("instance.actionType"), dataIndex: "action", key: "action", width: 120 },
    { title: t("instance.targetType"), dataIndex: "target_type", key: "target_type", width: 80 },
    { title: t("instance.targetId"), dataIndex: "target_id", key: "target_id" },
    {
      title: t("instance.changes"),
      key: "changes",
      render: (_, record) => (
        <div>
          {record.old_value && <div>{t("instance.oldValue")}: {JSON.stringify(record.old_value)}</div>}
          {record.new_value && <div>{t("instance.newValue")}: {JSON.stringify(record.new_value)}</div>}
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Tabs defaultActiveKey="overview">
        <TabPane tab={t("instance.overview")} key="overview">
          <Row gutter={16}>
            <Col span={6}>
              <Card loading={overviewLoading}>
                <Statistic title={t("instance.totalInstances")} value={overview?.total_instances || 0} />
              </Card>
            </Col>
            <Col span={6}>
              <Card loading={overviewLoading}>
                <Statistic title={t("instance.totalUsers")} value={overview?.total_users || 0} />
              </Card>
            </Col>
            <Col span={6}>
              <Card loading={overviewLoading}>
                <Statistic title={t("instance.warningInstances")} value={overview?.warning_instances || 0} valueStyle={{ color: "#fa8c16" }} />
              </Card>
            </Col>
            <Col span={6}>
              <Card loading={overviewLoading}>
                <Statistic title={t("instance.criticalInstances")} value={overview?.critical_instances || 0} valueStyle={{ color: "#f5222d" }} />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={t("instance.instanceManagement")} key="instances">
          <Card
            title={t("instance.instanceList")}
            extra={
              <Space>
                <Select
                  allowClear
                  placeholder={t("instance.filterSource")}
                  style={{ width: 150 }}
                  onChange={(v) => setInstanceFilter({ ...instanceFilter, source_id: v })}
                >
                  {sources.map((s) => (
                    <Select.Option key={s.source_id} value={s.source_id}>
                      {s.source_name}
                    </Select.Option>
                  ))}
                </Select>
                <Button icon={<ReloadOutlined />} onClick={loadInstances}>
                  {t("instance.refresh")}
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateInstance}>
                  {t("instance.addInstance")}
                </Button>
              </Space>
            }
          >
            <Table columns={instanceColumns} dataSource={instances} loading={instancesLoading} rowKey="instance_id" scroll={{ x: 1000 }} />
          </Card>
        </TabPane>

        <TabPane tab={t("instance.userAllocation")} key="allocations">
          <Card
            title={t("instance.allocationList")}
            extra={
              <Space>
                <Input
                  placeholder={t("instance.searchUserId")}
                  style={{ width: 200 }}
                  value={allocationFilter.user_id || ""}
                  onChange={(e) => setAllocationFilter({ ...allocationFilter, user_id: e.target.value || undefined })}
                  allowClear
                />
                <Select
                  allowClear
                  placeholder={t("instance.filterSource")}
                  style={{ width: 150 }}
                  onChange={(v) => setAllocationFilter({ ...allocationFilter, source_id: v })}
                  value={allocationFilter.source_id}
                >
                  {sources.map((s) => (
                    <Select.Option key={s.source_id} value={s.source_id}>
                      {s.source_name}
                    </Select.Option>
                  ))}
                </Select>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateAllocation}>
                  {t("instance.addAllocation")}
                </Button>
              </Space>
            }
          >
            <Table
              columns={allocationColumns}
              dataSource={allocations}
              loading={allocationsLoading}
              rowKey="id"
              pagination={{
                current: allocationPage,
                total: allocationsTotal,
                pageSize: 10,
                showTotal: (total) => t("instance.totalItems", { total }),
                onChange: setAllocationPage,
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab={t("instance.operationLogs")} key="logs">
          <Card
            title={t("instance.operationLogs")}
            extra={
              <Space>
                <Select
                  allowClear
                  placeholder={t("instance.filterAction", "Filter action")}
                  style={{ width: 150 }}
                  onChange={(v) => setLogsFilter({ ...logsFilter, action: v })}
                  value={logsFilter.action}
                >
                  <Select.Option value="create_instance">{t("instance.createInstance", "Create Instance")}</Select.Option>
                  <Select.Option value="update_instance">{t("instance.updateInstance", "Update Instance")}</Select.Option>
                  <Select.Option value="delete_instance">{t("instance.deleteInstance", "Delete Instance")}</Select.Option>
                  <Select.Option value="allocate">{t("instance.allocate", "Allocate")}</Select.Option>
                  <Select.Option value="migrate">{t("instance.migrate", "Migrate")}</Select.Option>
                  <Select.Option value="delete_allocation">{t("instance.deleteAllocation", "Delete Allocation")}</Select.Option>
                </Select>
                <Select
                  allowClear
                  placeholder={t("instance.filterTargetType", "Filter target type")}
                  style={{ width: 120 }}
                  onChange={(v) => setLogsFilter({ ...logsFilter, target_type: v })}
                  value={logsFilter.target_type}
                >
                  <Select.Option value="instance">{t("instance.instance", "Instance")}</Select.Option>
                  <Select.Option value="user">{t("instance.user", "User")}</Select.Option>
                  <Select.Option value="source">{t("instance.source", "Source")}</Select.Option>
                </Select>
              </Space>
            }
          >
            <Table
              columns={logColumns}
              dataSource={logs}
              loading={logsLoading}
              rowKey="id"
              pagination={{
                current: logsPage,
                total: logsTotal,
                pageSize: 10,
                showTotal: (total) => t("instance.totalItems", { total }),
                onChange: setLogsPage,
              }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* Instance Drawer */}
      <Drawer
        title={editingInstance ? t("instance.editInstance") : t("instance.addInstance")}
        open={instanceDrawerOpen}
        onClose={() => setInstanceDrawerOpen(false)}
        width={500}
      >
        <Form form={instanceForm} layout="vertical" onFinish={handleSaveInstance}>
          <Form.Item name="instance_id" label={t("instance.instanceId")} rules={[{ required: true, message: t("instance.required") }]}>
            <Input disabled={!!editingInstance} />
          </Form.Item>
          <Form.Item name="instance_name" label={t("instance.instanceName")} rules={[{ required: true, message: t("instance.required") }]}>
            <Input />
          </Form.Item>
          <Form.Item name="instance_url" label={t("instance.instanceUrl")} rules={[{ required: true, message: t("instance.required") }]}>
            <Input />
          </Form.Item>
          <Form.Item name="source_id" label={t("instance.belongToSource")} rules={[{ required: true, message: t("instance.required") }]}>
            <Select disabled={!!editingInstance}>
              {sources.map((s) => (
                <Select.Option key={s.source_id} value={s.source_id}>
                  {s.source_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="bbk_id" label={t("instance.belongToBranch")}>
            <Select allowClear disabled={!!editingInstance}>
              {BRANCHES.map((b) => (
                <Select.Option key={b.bbk_id} value={b.bbk_id}>
                  {b.bbk_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="max_users" label={t("instance.userThreshold")} rules={[{ required: true, message: t("instance.required") }]}>
            <Input type="number" min={1} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {t("instance.save")}
              </Button>
              <Button onClick={() => setInstanceDrawerOpen(false)}>{t("instance.cancel")}</Button>
            </Space>
          </Form.Item>
        </Form>
      </Drawer>

      {/* Allocation Drawer */}
      <Drawer
        title={t("instance.addAllocation")}
        open={allocationDrawerOpen}
        onClose={() => setAllocationDrawerOpen(false)}
        width={400}
      >
        <Form form={allocationForm} layout="vertical" onFinish={handleSaveAllocation}>
          <Form.Item name="user_id" label={t("instance.userId")} rules={[{ required: true, message: t("instance.required") }]}>
            <Input />
          </Form.Item>
          <Form.Item name="source_id" label={t("instance.belongToSource")} rules={[{ required: true, message: t("instance.required") }]}>
            <Select>
              {sources.map((s) => (
                <Select.Option key={s.source_id} value={s.source_id}>
                  {s.source_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="instance_id" label={t("instance.specifyInstance")} extra={t("instance.autoAllocateHint")}>
            <Select allowClear>
              {instances.map((i) => (
                <Select.Option key={i.instance_id} value={i.instance_id}>
                  {i.instance_name} ({i.current_users}/{i.max_users})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {t("instance.addAllocation")}
              </Button>
              <Button onClick={() => setAllocationDrawerOpen(false)}>{t("instance.cancel")}</Button>
            </Space>
          </Form.Item>
        </Form>
      </Drawer>

      {/* Migrate Drawer */}
      <Drawer
        title={t("instance.migrate")}
        open={migrateDrawerOpen}
        onClose={() => setMigrateDrawerOpen(false)}
        width={400}
      >
        <Form form={migrateForm} layout="vertical" onFinish={handleSaveMigrate}>
          <Form.Item label={t("instance.userId")}>
            <Input value={migratingAllocation?.user_id} disabled />
          </Form.Item>
          <Form.Item name="target_instance_id" label={t("instance.targetInstance")} rules={[{ required: true, message: t("instance.required") }]}>
            <Select>
              {instances
                .filter((i) => i.source_id === migratingAllocation?.source_id)
                .map((i) => (
                  <Select.Option key={i.instance_id} value={i.instance_id}>
                    {i.instance_name} ({i.current_users}/{i.max_users})
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {t("instance.migrate")}
              </Button>
              <Button onClick={() => setMigrateDrawerOpen(false)}>{t("instance.cancel")}</Button>
            </Space>
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}

export default InstancePage;
