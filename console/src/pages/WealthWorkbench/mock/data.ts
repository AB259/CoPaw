/**
 * 智能财富工作台 —— mock 静态数据
 * 规划数据已随接口闭环移除；本文件保留的是外部接口未就绪前的占位数据
 * （场景兜底 / 客户与触达 / 账户 / 分发用户池），随各接口接入逐步删除。
 */
import type { Account, Customer, DistributeTarget, Scene } from "../types";

/** 平台可用能力总量（示例），不随本期覆盖场景筛选缩减 */
export const PLATFORM_CAPABILITY_COUNT = 12;

export const accounts: Account[] = [
  {
    id: "rm",
    name: "张**",
    role: "客户经理",
    department: "xxx支行",
    source: "我的关注",
  },
  {
    id: "president",
    name: "李**",
    role: "支行行长",
    department: "xxxx支行",
    source: "行长关注",
  },
  {
    id: "middle",
    name: "王**",
    role: "分行中台",
    department: "xxxx 分行",
    source: "分行关注",
  },
];

/**
 * 分发目标用户池（mock）：无父系统身份的本地开发环境兜底数据，
 * 模拟「本分行下的客户经理列表」。嵌入环境走真实接口，见 distributeTargets.ts。
 * 人数特意给足，便于验证列表滚动、已选标签滚动与弹窗名单截断的样式效果。
 */
export const distributeTargets: DistributeTarget[] = [
  { sapId: "zhangwl", name: "张**", orgName: "xxx支行" },
  { sapId: "chenjy", name: "陈**", orgName: "xxx支行" },
  { sapId: "liuxt", name: "刘**", orgName: "xxx支行" },
  { sapId: "zhaom", name: "赵**", orgName: "xxx支行营业部" },
  { sapId: "sunq", name: "孙**", orgName: "xxx支行营业部" },
  { sapId: "zhouhr", name: "周**", orgName: "xx社区支行" },
  { sapId: "wuj", name: "吴**", orgName: "xxx支行" },
  { sapId: "zhengf", name: "郑**", orgName: "xxx支行" },
  { sapId: "wangly", name: "王**", orgName: "xxx支行营业部" },
  { sapId: "fengc", name: "冯**", orgName: "xxx支行营业部" },
  { sapId: "chux", name: "褚**", orgName: "xx社区支行" },
  { sapId: "weiy", name: "卫**", orgName: "xx社区支行" },
  { sapId: "jiangsh", name: "蒋**", orgName: "xxx支行" },
  { sapId: "shenh", name: "沈**", orgName: "xxx支行" },
  { sapId: "hanjy", name: "韩**", orgName: "xxx支行营业部" },
  { sapId: "yangf", name: "杨**", orgName: "xxx支行营业部" },
  { sapId: "zhuy", name: "朱**", orgName: "xx社区支行" },
  { sapId: "qiny", name: "秦**", orgName: "xxx支行" },
  { sapId: "youx", name: "尤**", orgName: "xxx支行" },
  { sapId: "xuh", name: "许**", orgName: "xxx支行营业部" },
  { sapId: "hel", name: "何**", orgName: "xxx支行营业部" },
  { sapId: "lvj", name: "吕**", orgName: "xx社区支行" },
  { sapId: "shir", name: "施**", orgName: "xxx支行" },
  { sapId: "kongw", name: "孔**", orgName: "xxx支行" },
  { sapId: "caoy", name: "曹**", orgName: "xxx支行营业部" },
  { sapId: "yanh", name: "严**", orgName: "xxx支行营业部" },
  { sapId: "huaj", name: "华**", orgName: "xx社区支行" },
  { sapId: "jinw", name: "金**", orgName: "xx社区支行" },
  { sapId: "weit", name: "魏**", orgName: "xxx支行" },
  { sapId: "taoj", name: "陶**", orgName: "xxx支行" },
  { sapId: "jiangy", name: "姜**", orgName: "xxx支行营业部" },
  { sapId: "qif", name: "戚**", orgName: "xxx支行营业部" },
  { sapId: "xiey", name: "谢**", orgName: "xx社区支行" },
  { sapId: "zoum", name: "邹**", orgName: "xxx支行" },
];

/** 产品大类：中文名 ↔ 英文 code，与后端 CATEGORY_CODE_BY_LABEL 一致 */
export const SCENE_CATEGORIES = [
  { label: "保险", code: "insurance" },
  { label: "理财", code: "finance" },
  { label: "存款", code: "deposit" },
  { label: "代发", code: "payroll" },
  { label: "跨境", code: "cross_border" },
  { label: "基金", code: "fund" },
] as const;

/**
 * 场景池的离线兜底（后端不可达的本地开发环境用）。
 * id 与后端 scene_fallback.py 的兜底数据保持一致，避免离线/在线切换错位。
 */
export const scenes: Scene[] = [
  {
    id: "skill-wealth-insurance-1",
    itemId: "item-wealth-insurance-1",
    name: "保障潜客经营",
    category: "保险",
    categoryCode: "insurance",
    icon: "shield",
    desc: "挖掘高潜保险客户，提升保险客户覆盖",
    ready: true,
    source: "总部预置",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-insurance"],
  },
  {
    id: "skill-wealth-insurance-2",
    itemId: "item-wealth-insurance-2",
    name: "保障缺口经营",
    category: "保险",
    categoryCode: "insurance",
    icon: "safe",
    desc: "识别客户保障缺口，提供综合保障方案",
    ready: true,
    source: "总部预置",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-insurance"],
  },
  {
    id: "skill-wealth-finance-3",
    itemId: "item-wealth-finance-3",
    name: "产品到期承接",
    category: "理财",
    categoryCode: "finance",
    icon: "layer",
    desc: "优先承接近期到期资金，提升客户资产留存",
    ready: true,
    source: "总部预置",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-wealth"],
  },
  {
    id: "skill-wealth-deposit-4",
    itemId: "item-wealth-deposit-4",
    name: "高价值揽客",
    category: "存款",
    categoryCode: "deposit",
    icon: "chart",
    desc: "挖掘客户资金变动机会，提升存款贡献",
    ready: true,
    source: "分行自建",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-deposit"],
  },
  {
    id: "skill-wealth-payroll-5",
    itemId: "item-wealth-payroll-5",
    name: "代发客户经营",
    category: "代发",
    categoryCode: "payroll",
    icon: "user",
    desc: "深化代发客户产品覆盖，提升存款贡献",
    ready: true,
    source: "总部预置",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-payroll"],
  },
  {
    id: "skill-wealth-finance-6",
    itemId: "item-wealth-finance-6",
    name: "理财重点客户经营",
    category: "理财",
    categoryCode: "finance",
    icon: "pie",
    desc: "提升理财配置比例，增强客户黏性",
    ready: true,
    source: "分行自建",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-wealth"],
  },
  {
    id: "skill-wealth-cross_border-7",
    itemId: "item-wealth-cross_border-7",
    name: "跨境客户经营",
    category: "跨境",
    categoryCode: "cross_border",
    icon: "globe",
    desc: "拓展跨境客户，提升国际业务贡献",
    ready: false,
    source: "总部预置",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-cross-border"],
  },
  {
    id: "skill-wealth-fund-8",
    itemId: "item-wealth-fund-8",
    name: "基金定投提升",
    category: "基金",
    categoryCode: "fund",
    icon: "layer",
    desc: "推动基金定投业务发展",
    ready: true,
    source: "总部预置",
    cronExample: "0 9 * * *",
    mcpRelations: ["mcp-customer", "mcp-fund"],
  },
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
    const scene = scenes[i % scenes.length];
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
