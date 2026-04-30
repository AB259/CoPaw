/**
 * MCP 上传弹窗
 */
import { useState } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Upload,
  message,
  Typography,
  Alert,
} from "antd";
import { UploadOutlined, InboxOutlined } from "@ant-design/icons";
import { marketMcpApi } from "../../api/modules/marketMcp";
import { BBK_ID_MAP } from "../../constants/bbk";
import type { MCPConfigDetail } from "../../api/types";

const { TextArea } = Input;
const { Text } = Typography;
const { Dragger } = Upload;

interface MCPUploadModalProps {
  open: boolean;
  sourceId: string;
  userId: string;
  userName: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function MCPUploadModal({
  open,
  sourceId,
  userId,
  userName,
  onClose,
  onSuccess,
}: MCPUploadModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [fileContent, setFileContent] = useState<MCPConfigDetail | null>(null);
  const [fileName, setFileName] = useState<string>("");

  // 解析上传的 JSON 文件
  const parseFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const parsed = JSON.parse(content) as MCPConfigDetail;

        // 验证必要的字段
        if (!parsed.name || !parsed.transport) {
          message.error("文件格式不正确：缺少 name 或 transport 字段");
          return;
        }

        setFileContent(parsed);
        setFileName(file.name);

        // 填充表单
        form.setFieldsValue({
          name: parsed.name,
          client_key: file.name.replace(/\.(json|mcp\.json)$/i, "").replace(/[^a-zA-Z0-9_-]/g, "-"),
          description: parsed.description || "",
        });

        message.success("文件解析成功");
      } catch {
        message.error("无法解析 JSON 文件");
      }
    };
    reader.readAsText(file);
    return false; // 阻止自动上传
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (!fileContent) {
        message.error("请先上传 MCP 配置文件");
        return;
      }

      setLoading(true);

      await marketMcpApi.uploadMCP(sourceId, userId, userName, {
        client_key: values.client_key,
        name: values.name,
        description: values.description,
        category_id: values.category_id,
        bbk_ids: values.bbk_ids,
        config: fileContent,
      });

      message.success("上传成功");
      form.resetFields();
      setFileContent(null);
      setFileName("");
      onSuccess();
      onClose();
    } catch (err) {
      console.error("上传失败:", err);
      message.error("上传失败");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    form.resetFields();
    setFileContent(null);
    setFileName("");
    onClose();
  };

  return (
    <Modal
      open={open}
      onCancel={handleClose}
      title="上传 MCP 连接器"
      width={600}
      footer={[
        <Button key="cancel" onClick={handleClose}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          上传
        </Button>,
      ]}
    >
      <Alert
        type="info"
        message="上传 .json 格式的 MCP 配置文件，系统将自动解析 name 和 client_key"
        style={{ marginBottom: 16 }}
        showIcon
      />

      <Dragger
        accept=".json"
        beforeUpload={parseFile}
        showUploadList={false}
        style={{ marginBottom: 16 }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域</p>
        <p className="ant-upload-hint">支持 .json 格式的 MCP 配置文件</p>
      </Dragger>

      {fileName && (
        <Alert
          type="success"
          message={`已解析文件: ${fileName}`}
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      <Form form={form} layout="vertical">
        <Form.Item
          name="client_key"
          label="Client Key"
          rules={[{ required: true, message: "请输入 Client Key" }]}
        >
          <Input placeholder="唯一标识，如 weather-tool" />
        </Form.Item>

        <Form.Item
          name="name"
          label="名称"
          rules={[{ required: true, message: "请输入名称" }]}
        >
          <Input placeholder="显示名称" />
        </Form.Item>

        <Form.Item name="description" label="描述">
          <TextArea rows={2} placeholder="MCP 描述" />
        </Form.Item>

        <Form.Item name="category_id" label="分类">
          <Select allowClear placeholder="选择分类" options={[]} />
        </Form.Item>

        <Form.Item name="bbk_ids" label="可见机构">
          <Select
            mode="multiple"
            allowClear
            placeholder="不选择则全员可见"
            options={BBK_ID_MAP}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}