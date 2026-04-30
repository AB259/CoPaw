import { Drawer, Descriptions, Table, Typography } from "antd";
import { MarketSkillDetail } from "../../api/modules/market";

const { Title } = Typography;

interface SkillDetailDrawerProps {
  open: boolean;
  skill: MarketSkillDetail | null;
  onClose: () => void;
}

export function SkillDetailDrawer({ open, skill, onClose }: SkillDetailDrawerProps) {
  if (!skill) return null;

  const userStatsColumns = [
    { title: "用户ID", dataIndex: "user_id", key: "user_id" },
    { title: "用户名称", dataIndex: "user_name", key: "user_name" },
    { title: "调用次数", dataIndex: "call_count", key: "call_count", sorter: (a: any, b: any) => a.call_count - b.call_count },
  ];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={640}
      title={<Title level={4}>{skill.name}</Title>}
    >
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="描述">{skill.description || "暂无"}</Descriptions.Item>
        <Descriptions.Item label="版本">{skill.version}</Descriptions.Item>
        <Descriptions.Item label="创建人">{skill.creator_name}</Descriptions.Item>
        <Descriptions.Item label="状态">
          {skill.status === "active" ? "上架中" : "已下架"}
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{skill.created_at || "-"}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{skill.updated_at || "-"}</Descriptions.Item>
        <Descriptions.Item label="调用次数">{skill.call_count}</Descriptions.Item>
        <Descriptions.Item label="用户量">{skill.user_count}</Descriptions.Item>
      </Descriptions>
      <Title level={5} style={{ marginTop: 24, marginBottom: 12 }}>
        调用客户明细
      </Title>
      <Table
        dataSource={skill.user_stats}
        columns={userStatsColumns}
        rowKey="user_id"
        pagination={{ pageSize: 10 }}
        size="small"
      />
    </Drawer>
  );
}