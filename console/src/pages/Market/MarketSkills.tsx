import { useEffect, useState } from "react";
import { Row, Col, Tree, Button, Empty, Spin, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { SkillCard } from "./SkillCard";
import { SkillDetailDrawer } from "./SkillDetailDrawer";
import { PublishModal } from "./PublishModal";
import { DistributeModal } from "./DistributeModal";
import { useMarket } from "./useMarket";
import { MarketSkill } from "../../api/modules/market";

const { Title } = Typography;

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

  useEffect(() => {
    refreshCategories();
    refreshSkills();
  }, [refreshCategories, refreshSkills]);

  const treeData = [
    { key: "all", title: "全部" },
    ...categories.map((c) => ({ key: String(c.id), title: c.name })),
  ];

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <div style={{ width: 200, borderRight: "1px solid #f0f0f0", padding: 16 }}>
        <Tree
          treeData={treeData}
          selectedKeys={[selectedCategory === null ? "all" : String(selectedCategory)]}
          onSelect={(keys) => {
            const key = keys[0] as string;
            setSelectedCategory(key === "all" ? null : Number(key));
          }}
          defaultExpandAll
        />
      </div>
      <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
        <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
          <Title level={4}>技能市场</Title>
          {isManager && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setPublishModalOpen(true)}>
              上架技能
            </Button>
          )}
        </div>
        {loading ? (
          <Spin />
        ) : skills.length === 0 ? (
          <Empty description="暂无技能" />
        ) : (
          <Row gutter={[16, 16]}>
            {skills.map((skill) => (
              <Col key={skill.item_id} xs={24} sm={12} md={8} lg={6}>
                <SkillCard
                  skill={skill}
                  onClick={() => openSkillDetail(skill.item_id)}
                  onDistribute={isManager ? () => openDistributeModal(skill) : undefined}
                  isManager={isManager}
                />
              </Col>
            ))}
          </Row>
        )}
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