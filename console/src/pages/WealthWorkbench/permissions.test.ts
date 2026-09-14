/**
 * 智能财富工作台 —— 角色与页面权限测试
 */
import { describe, expect, it, vi } from "vitest";
import {
  canAccessPage,
  FALLBACK_ROLE,
  needsDistributeTargets,
  POSITION_ROLE_MAP,
  resolveRole,
  ROLE_PERMISSIONS,
} from "./permissions";

describe("WealthWorkbench permissions", () => {
  it("矩阵与原型一致：三角色可看板/创建，仅客户经理有任务页", () => {
    for (const role of ["rm", "president", "middle"] as const) {
      expect(canAccessPage(role, "board")).toBe(true);
      expect(canAccessPage(role, "create")).toBe(true);
    }
    expect(canAccessPage("rm", "tasks")).toBe(true);
    expect(canAccessPage("president", "tasks")).toBe(false);
    expect(canAccessPage("middle", "tasks")).toBe(false);
  });

  it("矩阵覆盖全部角色", () => {
    expect(Object.keys(ROLE_PERMISSIONS).sort()).toEqual([
      "middle",
      "president",
      "rm",
    ]);
  });

  it("resolveRole 命中映射表", () => {
    const key = Object.keys(POSITION_ROLE_MAP)[0];
    if (key) {
      expect(resolveRole(key)).toBe(POSITION_ROLE_MAP[key]);
    } else {
      // 映射表当前为占位空表，跳过命中分支
      expect(POSITION_ROLE_MAP).toEqual({});
    }
  });

  it("仅行长/中台需要选择分发目标，客户经理发给自己", () => {
    expect(needsDistributeTargets("rm")).toBe(false);
    expect(needsDistributeTargets("president")).toBe(true);
    expect(needsDistributeTargets("middle")).toBe(true);
  });

  it("resolveRole 缺失或未知 positionId 回退默认角色", () => {
    expect(resolveRole(null)).toBe(FALLBACK_ROLE);
    expect(resolveRole(undefined)).toBe(FALLBACK_ROLE);
    expect(resolveRole("")).toBe(FALLBACK_ROLE);
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(resolveRole("UNKNOWN_POS")).toBe(FALLBACK_ROLE);
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });
});
