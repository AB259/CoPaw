import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Table,
  Card,
  Input,
  DatePicker,
  Spin,
  Tag,
  Descriptions,
  Timeline,
  Empty,
  Button,
} from "antd";
import {
  Search,
  MessageSquare,
  ChevronRight,
  Clock,
  FileText,
  Cpu,
  Zap,
} from "lucide-react";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import {
  tracingApi,
  SessionListItem,
  SessionStats,
  TraceListItem,
  TraceDetail,
} from "../../../api/modules/tracing";
import styles from "./index.module.less";

const { RangePicker } = DatePicker;

export default function SessionsPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchQuery, setSearchQuery] = useState("");
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  // 详情面板状态
  const [selectedSession, setSelectedSession] = useState<SessionListItem | null>(null);
  const [sessionStats, setSessionStats] = useState<SessionStats | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);

  // 对话列表状态
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [tracesTotal, setTracesTotal] = useState(0);
  const [tracesPage, setTracesPage] = useState(1);
  const [tracesLoading, setTracesLoading] = useState(false);

  // 对话详情状态
  const [selectedTrace, setSelectedTrace] = useState<TraceListItem | null>(null);
  const [traceDetail, setTraceDetail] = useState<TraceDetail | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, [page, pageSize, searchQuery, dateRange]);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const data = await tracingApi.getSessions(page, pageSize, {
        session_id: searchQuery || undefined,
        start_date: dateRange?.[0]?.format("YYYY-MM-DD"),
        end_date: dateRange?.[1]?.format("YYYY-MM-DD"),
      });
      setSessions(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessionDetail = async (session: SessionListItem) => {
    setSelectedSession(session);
    setSessionLoading(true);
    setTraces([]);
    setSelectedTrace(null);
    setTraceDetail(null);

    try {
      // 获取会话统计
      const stats = await tracingApi.getSessionStats(session.session_id);
      setSessionStats(stats);

      // 获取会话下的对话列表
      setTracesLoading(true);
      const tracesData = await tracingApi.getTraces(1, 20, {
        session_id: session.session_id,
      });
      setTraces(tracesData.items || []);
      setTracesTotal(tracesData.total || 0);
    } catch (error) {
      console.error("Failed to fetch session detail:", error);
    } finally {
      setSessionLoading(false);
      setTracesLoading(false);
    }
  };

  const fetchTraceDetail = async (trace: TraceListItem) => {
    setSelectedTrace(trace);
    setTraceLoading(true);
    try {
      const detail = await tracingApi.getTraceDetail(trace.trace_id);
      setTraceDetail(detail);
    } catch (error) {
      console.error("Failed to fetch trace detail:", error);
    } finally {
      setTraceLoading(false);
    }
  };

  const formatTokens = (tokens: number) => {
    if (!tokens) return "0";
    if (tokens < 1000) return tokens.toString();
    if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`;
    return `${(tokens / 1000000).toFixed(2)}M`;
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null || ms === undefined) return "-";
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "success";
      case "running":
        return "processing";
      case "error":
        return "error";
      case "cancelled":
        return "default";
      default:
        return "default";
    }
  };

  const columns: ColumnsType<SessionListItem> = [
    {
      title: t("analytics.sessionId", "Session ID"),
      dataIndex: "session_id",
      key: "session_id",
      width: 260,
      render: (v, record) => (
        <span
          style={{
            cursor: "pointer",
            color: selectedSession?.session_id === record.session_id ? "#1890ff" : undefined,
            fontWeight: selectedSession?.session_id === record.session_id ? 600 : 400,
          }}
        >
          {v}
        </span>
      ),
    },
    {
      title: t("analytics.userId", "User ID"),
      dataIndex: "user_id",
      key: "user_id",
      width: 180,
      ellipsis: true,
    },
    {
      title: t("analytics.channel", "Channel"),
      dataIndex: "channel",
      key: "channel",
      width: 100,
    },
    {
      title: t("analytics.traces", "Traces"),
      dataIndex: "total_traces",
      key: "total_traces",
      width: 80,
    },
    {
      title: t("analytics.tokens", "Tokens"),
      dataIndex: "total_tokens",
      key: "total_tokens",
      width: 100,
      render: (v) => formatTokens(v),
    },
    {
      title: t("analytics.skills", "Skills"),
      dataIndex: "total_skills",
      key: "total_skills",
      width: 80,
    },
    {
      title: t("analytics.lastActive", "Last Active"),
      dataIndex: "last_active",
      key: "last_active",
      width: 160,
      render: (v) => (v ? dayjs(v).format("MM-DD HH:mm") : "-"),
    },
  ];

  return (
    <div className={styles.sessionsPage}>
      <div className={styles.header}>
        <h2>{t("analytics.sessionAnalysis", "Session Analysis")}</h2>
        <div className={styles.filters}>
          <RangePicker
            value={dateRange}
            onChange={(dates) => {
              setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null);
              setPage(1);
            }}
            allowClear
          />
          <Input
            placeholder={t("analytics.searchSession", "Search session...")}
            prefix={<Search size={16} />}
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            style={{ width: 220 }}
            allowClear
          />
        </div>
      </div>

      <div className={styles.masterDetail}>
        {/* 会话列表 */}
        <div className={styles.masterPanel}>
          <Card className={styles.tableCard}>
            <Table
              dataSource={sessions}
              columns={columns}
              rowKey="session_id"
              loading={loading}
              scroll={{ x: 900 }}
              pagination={{
                current: page,
                pageSize,
                total,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => t("analytics.totalItems", { total }),
                onChange: (p, ps) => {
                  setPage(p);
                  setPageSize(ps);
                },
              }}
              onRow={(record) => ({
                onClick: () => fetchSessionDetail(record),
                style: {
                  cursor: "pointer",
                  backgroundColor:
                    selectedSession?.session_id === record.session_id ? "#e6f4ff" : undefined,
                },
              })}
            />
          </Card>
        </div>

        {/* 详情面板 */}
        <div className={styles.detailPanel}>
          {selectedSession ? (
            <>
              <div className={styles.detailHeader}>
                <h3>
                  <MessageSquare size={16} />
                  {t("analytics.sessionDetails", "Session Details")}
                </h3>
                <Button
                  type="text"
                  size="small"
                  onClick={() => {
                    setSelectedSession(null);
                    setSessionStats(null);
                    setTraces([]);
                    setSelectedTrace(null);
                    setTraceDetail(null);
                  }}
                >
                  {t("common.close", "Close")}
                </Button>
              </div>

              <div className={styles.detailBody}>
                {sessionLoading ? (
                  <div className={styles.loading}>
                    <Spin />
                  </div>
                ) : sessionStats ? (
                  <>
                    {/* 统计卡片 */}
                    <div className={styles.statsRow}>
                      <div className={styles.statItem}>
                        <div className={styles.value}>{sessionStats.total_traces}</div>
                        <div className={styles.label}>{t("analytics.traces", "Traces")}</div>
                      </div>
                      <div className={styles.statItem}>
                        <div className={styles.value}>{formatTokens(sessionStats.total_tokens)}</div>
                        <div className={styles.label}>{t("analytics.tokens", "Tokens")}</div>
                      </div>
                      <div className={styles.statItem}>
                        <div className={styles.value}>{formatDuration(sessionStats.avg_duration_ms)}</div>
                        <div className={styles.label}>{t("analytics.avgDuration", "Avg Duration")}</div>
                      </div>
                    </div>

                    {/* 基本信息 */}
                    <Descriptions column={2} size="small" bordered>
                      <Descriptions.Item label={t("analytics.userId", "User ID")} span={2}>
                        {sessionStats.user_id}
                      </Descriptions.Item>
                      <Descriptions.Item label={t("analytics.channel", "Channel")}>
                        {sessionStats.channel}
                      </Descriptions.Item>
                      <Descriptions.Item label={t("analytics.skills", "Skills")}>
                        {sessionStats.skills_used.length}
                      </Descriptions.Item>
                    </Descriptions>

                    {/* 模型使用 */}
                    {sessionStats.model_usage.length > 0 && (
                      <div className={styles.section}>
                        <h4>
                          <Cpu size={14} />
                          {t("analytics.modelUsage", "Model Usage")}
                        </h4>
                        <div className={styles.tagList}>
                          {sessionStats.model_usage.map((m) => (
                            <Tag key={m.model_name}>
                              {m.model_name}: {m.count}
                            </Tag>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 技能使用 */}
                    {sessionStats.skills_used.length > 0 && (
                      <div className={styles.section}>
                        <h4>
                          <Zap size={14} />
                          {t("analytics.skillsUsed", "Skills Used")}
                        </h4>
                        <div className={styles.tagList}>
                          {sessionStats.skills_used.map((s) => (
                            <Tag key={s.skill_name} color="blue">
                              {s.skill_name}: {s.count}
                            </Tag>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 对话列表 */}
                    <div className={styles.tracesSection}>
                      <h4>
                        <FileText size={14} />
                        {t("analytics.traces", "Traces")} ({tracesTotal})
                      </h4>

                      {tracesLoading ? (
                        <div className={styles.loading}>
                          <Spin />
                        </div>
                      ) : traces.length > 0 ? (
                        <div className={styles.tracesList}>
                          {traces.map((trace) => (
                            <div
                              key={trace.trace_id}
                              className={`${styles.traceItem} ${
                                selectedTrace?.trace_id === trace.trace_id ? styles.active : ""
                              }`}
                              onClick={() => fetchTraceDetail(trace)}
                            >
                              <div className={styles.traceHeader}>
                                <span className={styles.traceId}>
                                  {trace.trace_id.slice(0, 8)}...
                                </span>
                                <Tag color={getStatusColor(trace.status)}>{trace.status}</Tag>
                              </div>
                              <div className={styles.traceMeta}>
                                <span>{dayjs(trace.start_time).format("HH:mm:ss")}</span>
                                <span>{formatDuration(trace.duration_ms)}</span>
                                <span>{formatTokens(trace.total_tokens)} tokens</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Empty description={t("analytics.noTraces", "No traces")} />
                      )}
                    </div>

                    {/* 对话详情 */}
                    {selectedTrace && traceDetail && (
                      <div className={styles.section}>
                        <h4>
                          <Clock size={14} />
                          {t("analytics.traceTimeline", "Trace Timeline")}
                        </h4>
                        {traceLoading ? (
                          <div className={styles.loading}>
                            <Spin />
                          </div>
                        ) : (
                          <Timeline
                            items={traceDetail.spans.slice(0, 10).map((span) => ({
                              color: span.error ? "red" : "blue",
                              children: (
                                <div>
                                  <Tag>{span.event_type}</Tag>
                                  <span style={{ marginLeft: 8 }}>{span.name}</span>
                                  {span.duration_ms && (
                                    <span style={{ marginLeft: 8, color: "#999", fontSize: 12 }}>
                                      {formatDuration(span.duration_ms)}
                                    </span>
                                  )}
                                </div>
                              ),
                            }))}
                          />
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <Empty />
                )}
              </div>
            </>
          ) : (
            <div className={styles.emptyDetail}>
              <ChevronRight size={48} />
              <p>{t("analytics.selectSession", "Select a session to view details")}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
