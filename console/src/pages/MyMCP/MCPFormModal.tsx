/**
 * MCP 创建/编辑表单弹窗
 */
import { useEffect, useState } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Space,
  message,
  Typography,
} from "antd";
import { PlusOutlined, EditOutlined } from "@ant-design/icons";
import { useMyMCP } from "./useMyMCP";
import type { MyMCPDetail, MyMCPCreateRequest, MyMCPUpdateRequest } from "../../api/types";

const { TextArea } = Input;
const { Text } = Typography;

interface MCPFormModalProps {
  open: boolean;
  clientKey: string | null;
  initialData: MyMCPDetail | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function MCPFormModal({ open, clientKey, initialData, onClose, onSuccess }: MCPFormModalProps) {
  const [form] = Form.useForm();
  const { createMCP, updateMCP } = useMyMCP();
  const [loading, setLoading] = useState(false);
  const [transport, setTransport] = useState<string>("stdio");

  const isEdit = !!clientKey;

  useEffect(() => {
    if (open) {
      if (initialData) {
        // 编辑模式，填充初始数据
        form.setFieldsValue({
          client_key: initialData.client_key,
          name: initialData.name,
          description: initialData.description,
          transport: initialData.transport,
          url: initialData.url,
          command: initialData.command,
          args: initialData.args?.join(" "),
          cwd: initialData.cwd,
        });
        setTransport(initialData.transport);

        // 处理 env 和 headers
        if (initialData.env && Object.keys(initialData.env).length > 0) {
          const envLines = Object.entries(initialData.env)
            .map(([k, v]) => `${k}=${v}`)
            .join("\n");
          form.setFieldsValue({ env_text: envLines });
        }
        if (initialData.headers && Object.keys(initialData.headers).length > 0) {
          const headerLines = Object.entries(initialData.headers)
            .map(([k, v]) => `${k}: ${v}`)
            .join("\n");
          form.setFieldsValue({ headers_text: headerLines });
        }
      } else {
        // 创建模式，重置表单
        form.resetFields();
        setTransport("stdio");
      }
    }
  }, [open, initialData, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 解析 env 和 headers
      const env: Record<string, string> = {};
      const headers: Record<string, string> = {};

      if (values.env_text) {
        values.env_text.split("\n").forEach((line: string) => {
          const trimmed = line.trim();
          if (trimmed && trimmed.includes("=")) {
            const [key, ...valueParts] = trimmed.split("=");
            env[key.trim()] = valueParts.join("=").trim();
          }
        });
      }

      if (values.headers_text) {
        values.headers_text.split("\n").forEach((line: string) => {
          const trimmed = line.trim();
          if (trimmed && trimmed.includes(":")) {
            const [key, ...valueParts] = trimmed.split(":");
            headers[key.trim()] = valueParts.join(":").trim();
          }
        });
      }

      // 解析 args
      const args = values.args
        ? values.args.trim().split(/\s+/).filter(Boolean)
        : [];

      if (isEdit) {
        // 编辑模式
        const updateData: MyMCPUpdateRequest = {
          name: values.name,
          description: values.description,
          transport: values.transport,
          url: values.url,
          command: values.command,
          args,
          env,
          headers,
          cwd: values.cwd,
        };
        await updateMCP(clientKey!, updateData);
        message.success("更新成功");
      } else {
        // 创建模式
        const createData: MyMCPCreateRequest = {
          client_key: values.client_key,
          name: values.name,
          description: values.description,
          transport: values.transport,
          url: values.url,
          command: values.command,
          args,
          env,
          headers,
          cwd: values.cwd,
        };
        await createMCP(createData);
        message.success("创建成功");
      }

      onSuccess();
    } catch (err) {
      console.error("操作失败:", err);
      message.error("操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={isEdit ? <><EditOutlined /> 编辑 MCP</> : <><PlusOutlined /> 创建 MCP</>}
      width={600}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          {isEdit ? "保存" : "创建"}
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical" initialValues={{ transport: "stdio" }}>
        {/* client_key 只在创建时可编辑 */}
        <Form.Item
          name="client_key"
          label="Client Key"
          rules={[{ required: !isEdit, message: "请输入 Client Key" }]}
        >
          <Input disabled={isEdit} placeholder="唯一标识，如 weather-tool" />
        </Form.Item>

        <Form.Item
          name="name"
          label="名称"
          rules={[{ required: true, message: "请输入名称" }]}
        >
          <Input placeholder="显示名称，如 天气查询工具" />
        </Form.Item>

        <Form.Item name="description" label="描述">
          <TextArea rows={2} placeholder="工具描述" />
        </Form.Item>

        <Form.Item
          name="transport"
          label="传输类型"
          rules={[{ required: true }]}
        >
          <Select
            options={[
              { value: "stdio", label: "STDIO" },
              { value: "streamable_http", label: "HTTP" },
              { value: "sse", label: "SSE" },
            ]}
            onChange={(v) => setTransport(v)}
          />
        </Form.Item>

        {/* STDIO 配置 */}
        {transport === "stdio" && (
          <>
            <Form.Item
              name="command"
              label="命令"
              rules={[{ required: transport === "stdio", message: "请输入命令" }]}
            >
              <Input placeholder="如 npx" />
            </Form.Item>

            <Form.Item name="args" label="参数">
              <Input placeholder="用空格分隔，如 -y @example/mcp-server" />
            </Form.Item>

            <Form.Item name="env_text" label="环境变量">
              <TextArea
                rows={3}
                placeholder="每行一个，格式：KEY=value，如 API_KEY=sk-xxx"
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                脱敏值（如 se**********2345）将保留原值
              </Text>
            </Form.Item>

            <Form.Item name="cwd" label="工作目录">
              <Input placeholder="可选" />
            </Form.Item>
          </>
        )}

        {/* HTTP/SSE 配置 */}
        {transport !== "stdio" && (
          <>
            <Form.Item
              name="url"
              label="URL"
              rules={[{ required: transport !== "stdio", message: "请输入 URL" }]}
            >
              <Input placeholder="如 https://api.example.com/mcp" />
            </Form.Item>

            <Form.Item name="headers_text" label="Headers">
              <TextArea
                rows={3}
                placeholder="每行一个，格式：Header-Name: value"
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                脱敏值将保留原值
              </Text>
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  );
}