/**
 * 智能财富工作台 —— mock 静态数据
 * 规划、账户与分发用户池已随接口闭环移除；本文件保留的是外部接口未就绪前的
 * 占位数据（客户与触达），随各接口接入逐步删除。
 */
import type { Customer } from "../types";

/** 平台可用能力总量（示例），不随本期覆盖场景筛选缩减 */
export const PLATFORM_CAPABILITY_COUNT = 12;

/** 产品大类：中文名 ↔ 英文 code，与后端 CATEGORY_CODE_BY_LABEL 一致 */
export const SCENE_CATEGORIES = [
  { label: "保险", code: "insurance" },
  { label: "贷款", code: "loan" },
  { label: "存款", code: "deposit" },
  { label: "理财", code: "finance" },
  { label: "基金", code: "fund" },
  { label: "代发", code: "payroll" },
] as const;

/**
 * 客户清单占位的「场景名 ↔ 大类」对，仅供 buildCustomers 生成任务页演示数据；
 * 接入名单/触达接口后随客户 mock 整体删除。
 */
const CUSTOMER_TASK_SCENES: { name: string; category: string }[] = [
  { name: "保障潜客经营", category: "保险" },
  { name: "保障缺口经营", category: "保险" },
  { name: "信贷需求挖掘", category: "贷款" },
  { name: "高价值揽客", category: "存款" },
  { name: "产品到期承接", category: "理财" },
  { name: "理财重点客户经营", category: "理财" },
  { name: "基金定投提升", category: "基金" },
  { name: "代发客户经营", category: "代发" },
];

export const labels = ["总行重点", "分行重点", "行长指派"];

const names = [
  "张",
  "李",
  "王",
  "陈",
  "刘",
  "赵",
  "周",
  "吴",
  "孙",
  "郑",
  "钱",
  "冯",
  "朱",
  "许",
  "何",
  "吕",
  "施",
  "沈",
  "韩",
  "杨",
  "蒋",
  "曹",
  "严",
  "华",
  "金",
  "魏",
  "陶",
  "姜",
];

const reasons = [
  "产品将于 3 日后到期，预计释放资金 50 万元",
  "近期发生高价值动账，存在承接机会",
  "代发客户沉淀资金增长，具备进一步经营潜力",
  "理财产品 5 日后到期，预计释放资金 100 万元",
  "当前资产配置偏低风险，可适当优化配置结构",
  "到期资金暂未配置，存在承接机会",
  "基金持仓收益良好，存在加仓机会",
  "存款产品 7 日后到期，预计释放资金 80 万元",
  "近期活跃度提升，存在多产品交叉营销机会",
  "薪资代发客户，具备理财配置潜力",
];

const extraOpportunities: Record<number, string[]> = {
  1: [
    "近期新增大额活期资金，可进一步了解资金使用安排",
    "客户关注养老保障，可补充保险保障需求沟通",
  ],
  4: ["家庭资产以存款为主，存在多元化资产配置需求"],
  7: [
    "基金持有期限较长，可结合风险偏好沟通定投安排",
    "账户有闲置资金，可关注后续分批配置需求",
  ],
  10: ["工资结余持续增长，具备定期储蓄和长期配置潜力"],
};

export function buildCustomers(): Customer[] {
  return names.map((n, i) => {
    const done = i >= 19;
    // 客户清单为占位 mock：task/category 对齐真实场景名，
    // 便于任务页按场景筛选的交互演示；接入任务实例接口后整体替换。
    const scene = CUSTOMER_TASK_SCENES[i % CUSTOMER_TASK_SCENES.length];
    const c: Customer = {
      id: i + 1,
      name: n + "**",
      label: labels[(i + Math.floor(i / 3)) % 3],
      reason: reasons[i % 10],
      category: scene.category,
      task: scene.name,
      done,
      channel: done ? "电话" : "",
      time: done ? "2026-09-08 09:" + String(10 + i).padStart(2, "0") : "",
      note: done ? "已沟通客户需求，完成本次经营任务。" : "",
    };
    c.opportunities = [c.reason, ...(extraOpportunities[c.id] || [])];
    return c;
  });
}

export function buildHistory(): Customer[] {
  return Array.from({ length: 34 }, (_, i) => ({
    id: 100 + i,
    name: names[i % 28] + "**",
    label: labels[i % 3],
    reason: reasons[i % 10],
    category: "理财",
    task: "产品到期承接",
    done: true,
    channel: ["电话", "企微", "线上面访"][i % 3],
    time:
      "2026-09-07 " +
      (i % 2 ? "14" : "10") +
      ":" +
      String(i % 60).padStart(2, "0"),
    note: "已完成客户触达与需求记录。",
  }));
}
