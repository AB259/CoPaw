import { Descriptions, Tag } from "antd";
import { useTranslation } from "react-i18next";
import { UserStats } from "../../../../../api/modules/tracing";

interface UserStatsHeaderProps {
  userStats: UserStats;
}

export default function UserStatsHeader({ userStats }: UserStatsHeaderProps) {
  const { t } = useTranslation();

  const formatTokens = (tokens: number) => {
    if (!tokens) return "0";
    if (tokens < 1000) return tokens.toString();
    if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`;
    return `${(tokens / 1000000).toFixed(2)}M`;
  };

  const formatDuration = (ms: number) => {
    if (!ms) return "-";
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <div>
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label={t("analytics.totalSessions", "总会话数")} span={1}>
          {userStats.total_sessions}
        </Descriptions.Item>
        <Descriptions.Item label={t("analytics.conversations", "对话数")} span={1}>
          {userStats.total_conversations}
        </Descriptions.Item>
        <Descriptions.Item label={t("analytics.totalTokens", "总 Token")} span={1}>
          {formatTokens(userStats.total_tokens)}
        </Descriptions.Item>
        <Descriptions.Item label={t("analytics.avgDuration", "平均时长")} span={1}>
          {formatDuration(userStats.avg_duration_ms)}
        </Descriptions.Item>
        <Descriptions.Item label={t("analytics.inputTokens", "输入 Token")} span={1}>
          {formatTokens(userStats.input_tokens)}
        </Descriptions.Item>
        <Descriptions.Item label={t("analytics.outputTokens", "输出 Token")} span={1}>
          {formatTokens(userStats.output_tokens)}
        </Descriptions.Item>
      </Descriptions>

      {/* 模型使用 */}
      {userStats.model_usage.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <span style={{ fontWeight: 500, marginRight: 8 }}>模型使用:</span>
          {userStats.model_usage.map((m) => (
            <Tag key={m.model_name} style={{ marginBottom: 4 }}>
              {m.model_name}: {m.count} calls
            </Tag>
          ))}
        </div>
      )}

      {/* 工具使用 */}
      {userStats.tools_used.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <span style={{ fontWeight: 500, marginRight: 8 }}>工具使用:</span>
          {userStats.tools_used.map((tool) => (
            <Tag
              key={tool.tool_name}
              color={tool.error_count > 0 ? "error" : "default"}
              style={{ marginBottom: 4 }}
            >
              {tool.tool_name}: {tool.count} calls
            </Tag>
          ))}
        </div>
      )}

      {/* 技能使用 */}
      {userStats.skills_used.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <span style={{ fontWeight: 500, marginRight: 8 }}>技能使用:</span>
          {userStats.skills_used.map((s) => (
            <Tag key={s.skill_name} color="blue" style={{ marginBottom: 4 }}>
              {s.skill_name}: {s.count} calls
            </Tag>
          ))}
        </div>
      )}
    </div>
  );
}
