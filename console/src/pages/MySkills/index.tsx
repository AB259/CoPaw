import { useEffect, useState, useRef } from "react";
import { Typography, Card, Spin, Button, Space, Input, message, Tag, Empty } from "antd";
import { PlusOutlined, UploadOutlined, ReloadOutlined, ShopOutlined, ChevronRightOutlined, ChevronDownOutlined, FolderOutlined, FileTextOutlined, SparklesOutlined, ShopFilled } from "@ant-design/icons";
import { useMySkills } from "./useMySkills";
import { useIframeStore } from "../../stores/iframeStore";
import { getUserId } from "../../utils/identity";
import { DEFAULT_SOURCE_ID } from "../../constants/identity";
import { MySkill } from "../../api/modules/mySkills";

const { Title, Text } = Typography;

export default function MySkillsPage() {
  const sourceId = useIframeStore((state) => state.source) || DEFAULT_SOURCE_ID;
  const bbkId = useIframeStore((state) => state.bbk) || "100";
  const isManager = useIframeStore((state) => state.manager) || false;
  const userId = getUserId();
  const { createdSkills, receivedSkills, loading, refresh } = useMySkills(sourceId, userId);
  const [searchText, setSearchText] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedSkill, setSelectedSkill] = useState<MySkill | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(["created", "received"]));
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Debounce search
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const handleSearchChange = (value: string) => {
    setSearchText(value);
    clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => setDebouncedQuery(value), 200);
  };

  useEffect(() => {
    refresh();
    return () => clearTimeout(debounceTimer.current);
  }, [refresh]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    message.info(`上传功能开发中: ${file.name}`);
    e.target.value = "";
  };

  // Filter skills
  const filterSkills = (skills: MySkill[]) => {
    const q = debouncedQuery.trim().toLowerCase();
    if (!q) return skills;
    return skills.filter((s) =>
      s.skill_name.toLowerCase().includes(q) ||
      (s.description?.toLowerCase().includes(q) ?? false)
    );
  };

  const filteredCreated = filterSkills(createdSkills);
  const filteredReceived = filterSkills(receivedSkills);

  const toggleGroup = (key: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleSelectSkill = (skill: MySkill) => {
    setSelectedSkill(skill);
  };

  // Navigate to marketplace (would need to be implemented with routing)
  const goToMarketplace = () => {
    message.info("跳转到应用市场功能开发中");
  };

  // Skill list item component
  const SkillListItem = ({ skill, isSelected }: { skill: MySkill; isSelected: boolean }) => (
    <div
      onClick={() => handleSelectSkill(skill)}
      style={{
        padding: "8px 10px",
        borderRadius: 8,
        cursor: "pointer",
        backgroundColor: isSelected ? "#e6f4ff" : "transparent",
        border: isSelected ? "1px solid #1677ff" : "1px solid transparent",
        marginBottom: 4,
        transition: "all 0.15s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
        <FileTextOutlined style={{ color: "#87867f", flexShrink: 0 }} />
        <Text
          strong={isSelected}
          style={{
            flex: 1,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            color: isSelected ? "#1677ff" : "#141413",
          }}
        >
          {skill.skill_name}
        </Text>
        {skill.version && (
          <Tag style={{ fontSize: 10, margin: 0, borderRadius: 999 }}>v{skill.version}</Tag>
        )}
      </div>
    </div>
  );

  // Skill group section
  const SkillGroup = ({
    title,
    skills,
    groupKey,
    style,
  }: {
    title: string;
    skills: MySkill[];
    groupKey: string;
    style?: React.CSSProperties;
  }) => {
    const isExpanded = expandedGroups.has(groupKey);

    const headerStyle = (() => {
      if (title.includes("创建")) {
        return {
          borderColor: "#f5d9c4",
          backgroundColor: "#fdf3e7",
          color: "#8b623d",
          dotColor: "#c4956a",
        };
      }
      if (title.includes("接收")) {
        return {
          borderColor: "#c4e8d1",
          backgroundColor: "#edf7f0",
          color: "#2e7d4f",
          dotColor: "#5db872",
        };
      }
      return {
        borderColor: "#e8e6dc",
        backgroundColor: "#f5f4ed",
        color: "#5e5d59",
        dotColor: "#87867f",
      };
    })();

    return (
      <div
        style={{
          borderRadius: 12,
          border: "1px solid #e8e6dc",
          backgroundColor: "rgba(255,255,255,0.4)",
          padding: 6,
          ...style,
        }}
      >
        <div
          onClick={() => toggleGroup(groupKey)}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "6px 10px",
            borderRadius: 8,
            cursor: "pointer",
            border: `1px solid ${headerStyle.borderColor}`,
            backgroundColor: headerStyle.backgroundColor,
            transition: "background-color 0.15s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            {isExpanded ? (
              <ChevronDownOutlined style={{ fontSize: 12, color: "#87867f" }} />
            ) : (
              <ChevronRightOutlined style={{ fontSize: 12, color: "#87867f" }} />
            )}
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: headerStyle.dotColor,
                flexShrink: 0,
              }}
            />
            <Text style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.02em", color: headerStyle.color }}>
              {title}
            </Text>
          </div>
          <Tag
            style={{
              height: 20,
              minWidth: 24,
              justifyContent: "center",
              padding: "0 6px",
              fontSize: 10,
              fontWeight: 600,
              margin: 0,
              borderRadius: 999,
              backgroundColor: "#fff",
              border: `1px solid ${headerStyle.borderColor}`,
              color: headerStyle.color,
            }}
          >
            {skills.length}
          </Tag>
        </div>
        {isExpanded && (
          <div style={{ padding: "8px 2px 2px 2px" }}>
            {skills.length === 0 ? (
              <Text style={{ fontSize: 12, color: "#87867f", padding: "8px 10px", display: "block" }}>
                没有匹配的技能
              </Text>
            ) : (
              skills.map((skill) => (
                <SkillListItem
                  key={skill.skill_name}
                  skill={skill}
                  isSelected={selectedSkill?.skill_name === skill.skill_name}
                />
              ))
            )}
          </div>
        )}
      </div>
    );
  };

  // Skill detail panel
  const SkillDetailPanel = ({ skill }: { skill: MySkill | null }) => {
    if (!skill) {
      return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", padding: 32, textAlign: "center" }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              backgroundColor: "#f5f4ed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
            }}
          >
            <SparklesOutlined style={{ fontSize: 28, color: "#c4956a" }} />
          </div>
          <Title level={5} style={{ margin: "0 0 8px 0", color: "#141413" }}>
            技能详情
          </Title>
          <Text style={{ fontSize: 14, color: "#87867f" }}>
            选择左侧技能查看详情
          </Text>
        </div>
      );
    }

    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div
          style={{
            padding: 16,
            borderBottom: "1px solid #e8e6dc",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
              <Text strong style={{ fontSize: 16, color: "#141413" }}>
                {skill.skill_name}
              </Text>
              {skill.version && (
                <Tag style={{ fontSize: 11, borderRadius: 999 }}>v{skill.version}</Tag>
              )}
              {skill.source === "customized" && (
                <Tag color="green" style={{ fontSize: 11, borderRadius: 999 }}>自定义</Tag>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              {skill.category && (
                <Tag style={{ fontSize: 11, borderRadius: 999, backgroundColor: "#f5f4ed", border: "1px solid #e8e6dc" }}>
                  {skill.category}
                </Tag>
              )}
              {skill.creator_name && (
                <Text style={{ fontSize: 12, color: "#87867f" }}>
                  创建者: {skill.creator_name}
                </Text>
              )}
            </div>
          </div>
        </div>

        {/* Description */}
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #e8e6dc" }}>
          <Text style={{ fontSize: 14, color: "#87867f", whiteSpace: "pre-wrap" }}>
            {skill.description || "暂无描述"}
          </Text>
        </div>

        {/* Content placeholder */}
        <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
          <div
            style={{
              borderRadius: 12,
              border: "1px solid #e8e6dc",
              backgroundColor: "rgba(255,255,255,0.7)",
              padding: 16,
              minHeight: 200,
            }}
          >
            <Text type="secondary" style={{ fontSize: 12 }}>
              技能内容预览功能开发中…
            </Text>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ display: "flex", height: "100%", backgroundColor: "#f5f4ed" }}>
      {/* Left sidebar */}
      <div
        style={{
          width: 300,
          flexShrink: 0,
          borderRight: "1px solid #e8e6dc",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Search and actions */}
        <div style={{ padding: 12, borderBottom: "1px solid #e8e6dc" }}>
          <div style={{ position: "relative", marginBottom: 8 }}>
            <Input
              placeholder="搜索技能"
              value={searchText}
              onChange={(e) => handleSearchChange(e.target.value)}
              allowClear
              style={{
                height: 28,
                paddingLeft: 28,
                fontSize: 12,
                borderRadius: 8,
                border: "1px solid #e8e6dc",
              }}
            />
            <span style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", color: "#87867f" }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
            </span>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <Button
              size="small"
              icon={<UploadOutlined />}
              onClick={handleUploadClick}
              style={{
                flex: 1,
                height: 28,
                fontSize: 12,
                borderRadius: 8,
                border: "1px solid #d1cfc5",
                backgroundColor: "#fdf3e7",
                color: "#8b623d",
              }}
            >
              上传技能
            </Button>
            <Button
              size="small"
              icon={<ShopOutlined />}
              onClick={goToMarketplace}
              style={{
                flex: 1,
                height: 28,
                fontSize: 12,
                borderRadius: 8,
                border: "1px solid #e8e6dc",
                backgroundColor: "#f5f4ed",
                color: "#5e5d59",
              }}
            >
              去应用市场
              <ChevronRightOutlined style={{ fontSize: 10, marginLeft: 2 }} />
            </Button>
          </div>
        </div>

        {/* Skill groups */}
        <div style={{ flex: 1, overflow: "auto", padding: 8 }}>
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 100 }}>
              <Spin />
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <SkillGroup
                title="我创建的"
                skills={filteredCreated}
                groupKey="created"
              />
              <SkillGroup
                title="我接收的"
                skills={filteredReceived}
                groupKey="received"
              />
            </div>
          )}
        </div>
      </div>

      {/* Right detail panel */}
      <div style={{ flex: 1, backgroundColor: "#faf9f5", overflow: "hidden" }}>
        <SkillDetailPanel skill={selectedSkill} />
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".zip"
        style={{ display: "none" }}
        onChange={handleFileSelect}
      />
    </div>
  );
}
