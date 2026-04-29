import { Card, Tag, Typography } from "antd";
import { MarketSkill } from "../../api/modules/market";
import { Users, PhoneCall } from "lucide-react";

const { Text } = Typography;

interface SkillCardProps {
  skill: MarketSkill;
  onClick: () => void;
  onDistribute?: () => void;
  isManager: boolean;
}

export function SkillCard({ skill, onClick, onDistribute, isManager }: SkillCardProps) {
  return (
    <Card
      hoverable
      onClick={onClick}
      styles={{
        body: { padding: 16 },
      }}
    >
      <div style={{ marginBottom: 8 }}>
        <Text strong style={{ fontSize: 16 }}>
          {skill.name}
        </Text>
        {skill.category_id && (
          <Tag color="blue" style={{ marginLeft: 8 }}>
            {skill.category_id}
          </Tag>
        )}
      </div>
      <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        {skill.description || "暂无描述"}
      </Text>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {skill.creator_name} · v{skill.version}
        </Text>
        <div style={{ display: "flex", gap: 12 }}>
          <div
            style={{
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              borderRadius: 4,
              padding: "4px 8px",
              color: "#fff",
              fontSize: 12,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <PhoneCall size={12} />
            {skill.call_count}
          </div>
          <div
            style={{
              background: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
              borderRadius: 4,
              padding: "4px 8px",
              color: "#fff",
              fontSize: 12,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Users size={12} />
            {skill.user_count}
          </div>
        </div>
      </div>
    </Card>
  );
}