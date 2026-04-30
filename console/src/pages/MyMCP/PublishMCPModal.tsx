/**
 * 发布 MCP 到市场弹窗
 */
import { useState } from "react";
import {
  Modal,
  Form,
  Select,
  Button,
  message,
  List,
  Typography,
  Tag,
  Alert,
} from "antd";
import { RocketOutlined, CheckOutlined, CloseOutlined } from "@ant-design/icons";
import { myMcpApi } from "../../api/modules/myMcp";
import { BBK_ID_MAP } from "../../constants/bbk";
import type { PublishMCPResult } from "../../api/types";

const { Text } = Typography;

interface PublishMCPModalProps {
  open: boolean;
  sourceId: string;
  userId: string;
  userName: string;
  selectedKeys: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export function PublishMCPModal({
  open,
  sourceId,
  userId,
  userName,
  selectedKeys,
  onClose,
  onSuccess,
}: PublishMCPModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<PublishMCPResult[]>([]);

  const handleSubmit = async () => {
    if (selectedKeys.length === 0) {
      message.warning("请选择要发布的 MCP");
      return;
    }

    try {
      const values = await form.validateFields();
      setLoading(true);
      setResults([]);

      const response = await myMcpApi.publishToMarket(sourceId, userId, userName, {
        client_keys: selectedKeys,
        category_id: values.category_id,
        bbk_ids: values.bbk_ids,
      });

      setResults(response.results);

      const successCount = response.results.filter((r) => r.success).length;
      if (successCount === selectedKeys.length) {
        message.success(`全部发布成功 (${successCount} 个)`);
        onSuccess();
      } else {
        message.warning(`发布完成：${successCount} 成功，${selectedKeys.length - successCount} 失败`);
      }
    } catch (err) {
      console.error("发布失败:", err);
      message.error("发布失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={<><RocketOutlined /> 发布到市场</>}
      width={500}
      footer={[
        <Button key="cancel" onClick={onClose}>
          关闭
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          发布
        </Button>,
      ]}
    >
      <Alert
        type="info"
        message={`将发布 ${selectedKeys.length} 个 MCP 到应用市场`}
        style={{ marginBottom: 16 }}
        showIcon
      />

      <List
        dataSource={selectedKeys}
        renderItem={(key) => {
          const result = results.find((r) => r.client_key === key);
          return (
            <List.Item style={{ padding: "8px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, width: "100%" }}>
                <Text>{key}</Text>
                {result && (
                  <Tag color={result.success ? "green" : "red"}>
                    {result.success ? <CheckOutlined /> : <CloseOutlined />}
                    {result.success ? "成功" : "失败"}
                  </Tag>
                )}
                {result?.item_id && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    ID: {result.item_id}
                  </Text>
                )}
                {result?.error && (
                  <Text type="danger" style={{ fontSize: 12 }}>
                    {result.error}
                  </Text>
                )}
              </div>
            </List.Item>
          );
        }}
        style={{ marginBottom: 16 }}
      />

      <Form form={form} layout="vertical">
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