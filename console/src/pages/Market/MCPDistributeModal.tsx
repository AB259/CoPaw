/**
 * MCP 分发弹窗
 */
import { useState } from "react";
import {
  Modal,
  Form,
  Radio,
  Select,
  Button,
  Typography,
  message,
} from "antd";
import { RocketOutlined } from "@ant-design/icons";
import { marketMcpApi } from "../../api/modules/marketMcp";
import { BBK_ID_MAP } from "../../constants/bbk";
import type { MarketMCPItem } from "../../api/types";

const { Text } = Typography;

interface MCPDistributeModalProps {
  open: boolean;
  mcp: MarketMCPItem | null;
  sourceId: string;
  userId: string;
  userName: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function MCPDistributeModal({
  open,
  mcp,
  sourceId,
  userId,
  userName,
  onClose,
  onSuccess,
}: MCPDistributeModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [targetType, setTargetType] = useState<"all" | "bbk_id" | "user_id">("all");

  const handleSubmit = async () => {
    if (!mcp) return;

    try {
      const values = await form.validateFields();
      setLoading(true);

      await marketMcpApi.distributeMCP(
        sourceId,
        mcp.item_id,
        userId,
        userName,
        {
          target_type: targetType,
          target_values: targetType === "all" ? [] : values.target_values || [],
        }
      );

      message.success("分发成功");
      onSuccess();
      onClose();
    } catch (err) {
      console.error("分发失败:", err);
      message.error("分发失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={<><RocketOutlined /> 分发「{mcp?.name || ""}」</>}
      width={500}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          分发
        </Button>,
      ]}
    >
      <Text type="secondary" style={{ marginBottom: 16, display: "block" }}>
        将此 MCP 分发到目标用户的本地配置中
      </Text>

      <Form form={form} layout="vertical">
        <Form.Item label="分发目标">
          <Radio.Group value={targetType} onChange={(e) => setTargetType(e.target.value)}>
            <Radio value="all">全员</Radio>
            <Radio value="bbk_id">按机构</Radio>
            <Radio value="user_id">按用户</Radio>
          </Radio.Group>
        </Form.Item>

        {targetType === "bbk_id" && (
          <Form.Item name="target_values" label="选择机构" rules={[{ required: true, message: "请选择机构" }]}>
            <Select mode="multiple" placeholder="选择机构" options={BBK_ID_MAP} />
          </Form.Item>
        )}

        {targetType === "user_id" && (
          <Form.Item name="target_values" label="用户 ID" rules={[{ required: true, message: "请输入用户 ID" }]}>
            <Select mode="tags" placeholder="输入用户 ID，回车添加" />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}