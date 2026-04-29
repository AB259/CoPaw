import { useEffect, useState } from "react";
import { Input, Button, Empty, Spin, Typography, Select, Tag } from "antd";
import { PlusOutlined, SearchOutlined, ReloadOutlined, ShoppingBagOutlined } from "@ant-design/icons";
import { SkillCard } from "./SkillCard";
import { SkillDetailDrawer } from "./SkillDetailDrawer";
import { PublishModal } from "./PublishModal";
import { DistributeModal } from "./DistributeModal";
import { useMarket } from "./useMarket";
import { MarketSkill } from "../../api/modules/market";

const { Title, Text } = Typography;

interface MarketSkillsProps {
  sourceId: string;
  bbkId: string;
  userId: string;
  userName: string;
  isManager: boolean;
}

export function MarketSkills({ sourceId, bbkId, userId, userName, isManager }: MarketSkillsProps) {
  const {
    categories,
    skills,
    loading,
    selectedCategory,
    setSelectedCategory,
    selectedSkill,
    detailDrawerOpen,
    setDetailDrawerOpen,
    publishModalOpen,
    setPublishModalOpen,
    distributeModalOpen,
    setDistributeModalOpen,
    distributeTargetSkill,
    refreshCategories,
    refreshSkills,
    openSkillDetail,
    openDistributeModal,
  } = useMarket(sourceId, bbkId);

  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    refreshCategories();
    refreshSkills();
  }, [refreshCategories, refreshSkills]);

  // Filter skills by search query
  const filteredSkills = skills.filter((skill) => {
    const query = searchQuery.toLowerCase();
    return (
      skill.name.toLowerCase().includes(query) ||
      (skill.description?.toLowerCase().includes(query) ?? false) ||
      (skill.creator_name?.toLowerCase().includes(query) ?? false)
    );
  });

  // Filter by selected category
  const displayedSkills = selectedCategory === null
    ? filteredSkills
    : filteredSkills.filter((s) => String(s.category_id) === String(selectedCategory));

  // Calculate category counts
  const categoryCountMap = new Map<string | number, number>();
  skills.forEach((s) => {
    if (s.category_id) {
      const count = categoryCountMap.get(s.category_id) || 0;
      categoryCountMap.set(s.category_id, count + 1);
    }
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", backgroundColor: "#f5f4ed" }}>
      {/* Header */}
      <div style={{ padding: "16px 20px", borderBottom: "1px solid #e8e6dc", backgroundColor: "#faf9f5" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 12,
                backgroundColor: "#fdf3e7",
                border: "1px solid #f5d9c4",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ShoppingBagOutlined style={{ fontSize: 16, color: "#c4956a" }} />
            </div>
            <div>
              <Title level={5} style={{ margin: 0, color: "#141413" }}>
                技能市场
              </Title>
              <Text style={{ fontSize: 11, color: "#87867f" }}>发现并安装社区共享的技能资源</Text>
            </div>
          </div>
          {isManager && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setPublishModalOpen(true)}
              style={{
                backgroundColor: "#c4956a",
                borderColor: "#c4956a",
                borderRadius: 8,
              }}
            >
              上架技能
            </Button>
          )}
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <Input
            placeholder="搜索技能名称、描述…"
            prefix={<SearchOutlined style={{ color: "#87867f" }} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            allowClear
            style={{
              flex: 1,
              height: 36,
              borderRadius: 12,
              border: "1px solid #e8e6dc",
              backgroundColor: "#fff",
            }}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { refreshCategories(); refreshSkills(); }}
            style={{ borderRadius: 12, border: "1px solid #e8e6dc" }}
          />
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
        {/* Sidebar - Categories */}
        <div
          style={{
            width: 220,
            borderRight: "1px solid #e8e6dc",
            backgroundColor: "#faf9f5",
            padding: 12,
            overflow: "auto",
          }}
        >
          <div style={{ marginBottom: 8, padding: "0 4px" }}>
            <Text style={{ fontSize: 12, fontWeight: 500, color: "#5e5d59" }}>分类</Text>
            {selectedCategory !== null && (
              <Button
                type="link"
                size="small"
                style={{ fontSize: 12, color: "#b85a3a", padding: "0 0 0 8px" }}
                onClick={() => setSelectedCategory(null)}
              >
                清除
              </Button>
            )}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {/* All category */}
            <div
              onClick={() => setSelectedCategory(null)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "8px 10px",
                borderRadius: 12,
                cursor: "pointer",
                backgroundColor: selectedCategory === null ? "#fdf3e7" : "transparent",
                border: selectedCategory === null ? "1px solid #f5d9c4" : "1px solid transparent",
                color: selectedCategory === null ? "#8b623d" : "#5e5d59",
                transition: "all 0.15s ease",
              }}
            >
              <span style={{ fontSize: 13 }}>全部</span>
              <Tag
                style={{
                  fontSize: 11,
                  margin: 0,
                  backgroundColor: selectedCategory === null ? "#f5d9c4" : "#f0eee6",
                  color: selectedCategory === null ? "#8b623d" : "#87867f",
                  border: "none",
                  borderRadius: 999,
                }}
              >
                {skills.length}
              </Tag>
            </div>
            {/* Category items */}
            {categories.map((cat) => {
              const isActive = String(selectedCategory) === String(cat.id);
              const count = categoryCountMap.get(cat.id) || 0;
              return (
                <div
                  key={cat.id}
                  onClick={() => setSelectedCategory(isActive ? null : cat.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "8px 10px",
                    borderRadius: 12,
                    cursor: "pointer",
                    backgroundColor: isActive ? "#fdf3e7" : "transparent",
                    border: isActive ? "1px solid #f5d9c4" : "1px solid transparent",
                    color: isActive ? "#8b623d" : "#5e5d59",
                    transition: "all 0.15s ease",
                  }}
                >
                  <span style={{ fontSize: 13 }}>{cat.name}</span>
                  <Tag
                    style={{
                      fontSize: 11,
                      margin: 0,
                      backgroundColor: isActive ? "#f5d9c4" : "#f0eee6",
                      color: isActive ? "#8b623d" : "#87867f",
                      border: "none",
                      borderRadius: 999,
                    }}
                  >
                    {count}
                  </Tag>
                </div>
              );
            })}
          </div>
        </div>

        {/* Main content - Skill cards */}
        <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
          <div style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Text style={{ fontSize: 12, color: "#87867f" }}>
              {selectedCategory !== null
                ? `当前分类：${categories.find((c) => String(c.id) === String(selectedCategory))?.name || "未知"}`
                : "全部技能"}
              {" · 筛选结果 "}
              {displayedSkills.length} 个
            </Text>
          </div>

          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 200 }}>
              <Spin />
            </div>
          ) : displayedSkills.length === 0 ? (
            <Empty description={searchQuery ? "未找到匹配的技能" : "暂无技能"} />
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 12 }}>
              {displayedSkills.map((skill) => (
                <SkillCard
                  key={skill.item_id}
                  skill={skill}
                  onClick={() => openSkillDetail(skill.item_id)}
                  onDistribute={isManager ? () => openDistributeModal(skill) : undefined}
                  isManager={isManager}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <SkillDetailDrawer
        open={detailDrawerOpen}
        skill={selectedSkill}
        onClose={() => setDetailDrawerOpen(false)}
      />
      {isManager && (
        <>
          <PublishModal
            open={publishModalOpen}
            sourceId={sourceId}
            userId={userId}
            userName={userName}
            onClose={() => setPublishModalOpen(false)}
            onSuccess={refreshSkills}
          />
          <DistributeModal
            open={distributeModalOpen}
            skill={distributeTargetSkill}
            sourceId={sourceId}
            userId={userId}
            userName={userName}
            onClose={() => setDistributeModalOpen(false)}
            onSuccess={refreshSkills}
          />
        </>
      )}
    </div>
  );
}