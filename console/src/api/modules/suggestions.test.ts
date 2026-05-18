import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchSuggestions } from "./suggestions";

describe("suggestions api", () => {
  beforeEach(() => {
    window.__env__ = { baseUrl: "" };
    vi.restoreAllMocks();
    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    vi.stubGlobal("sessionStorage", {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    vi.useRealTimers();
  });

  it("returns mock suggestions from the frontend API path", async () => {
    vi.useFakeTimers();

    const promise = fetchSuggestions({
      chatId: "chat-1",
      turnId: "turn-1",
      userMessage: "帮我分析这个任务",
      assistantMessage: "分析完成",
    });
    await vi.advanceTimersByTimeAsync(500);

    await expect(promise).resolves.toEqual([
      "关于“帮我分析这个任务”能展开吗",
      "能给我一个执行建议吗",
      "还有哪些补充信息",
    ]);
  });

  it("returns default mock suggestions when user message is empty", async () => {
    vi.useFakeTimers();

    const promise = fetchSuggestions({
      chatId: "chat-1",
      turnId: "turn-1",
      userMessage: "  ",
      assistantMessage: "分析完成",
    });
    await vi.advanceTimersByTimeAsync(500);

    await expect(promise).resolves.toEqual([
      "能给我一个总结吗",
      "下一步该怎么做",
      "有哪些风险点需要注意",
    ]);
  });
});
