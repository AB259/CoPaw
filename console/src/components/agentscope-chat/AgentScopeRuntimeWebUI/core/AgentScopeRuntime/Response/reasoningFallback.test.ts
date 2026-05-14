import { describe, expect, it } from "vitest";
import {
  AgentScopeRuntimeContentType,
  AgentScopeRuntimeMessageRole,
  AgentScopeRuntimeMessageType,
  AgentScopeRuntimeRunStatus,
  IAgentScopeRuntimeResponse,
} from "../types";
import { getCompletedReasoningFallbackText } from "./reasoningFallback";

function response(
  overrides: Partial<IAgentScopeRuntimeResponse>,
): IAgentScopeRuntimeResponse {
  return {
    id: "response-1",
    object: "response",
    status: AgentScopeRuntimeRunStatus.Completed,
    created_at: 1,
    output: [],
    ...overrides,
  };
}

describe("getCompletedReasoningFallbackText", () => {
  it("returns the last reasoning text when completed output has no body message", () => {
    const data = response({
      output: [
        {
          id: "reason-1",
          object: "message",
          role: AgentScopeRuntimeMessageRole.ASSISTANT,
          type: AgentScopeRuntimeMessageType.REASONING,
          status: AgentScopeRuntimeRunStatus.Completed,
          content: [
            {
              object: "content",
              type: AgentScopeRuntimeContentType.TEXT,
              text: "  这是被误归类到 think 的正文  ",
              status: AgentScopeRuntimeRunStatus.Completed,
            },
          ],
        },
      ],
    });

    expect(getCompletedReasoningFallbackText(data)).toBe(
      "这是被误归类到 think 的正文",
    );
  });

  it("does not return fallback text before the stream is completed", () => {
    const data = response({
      status: AgentScopeRuntimeRunStatus.InProgress,
      output: [
        {
          id: "reason-1",
          object: "message",
          role: AgentScopeRuntimeMessageRole.ASSISTANT,
          type: AgentScopeRuntimeMessageType.REASONING,
          status: AgentScopeRuntimeRunStatus.InProgress,
          content: [
            {
              object: "content",
              type: AgentScopeRuntimeContentType.TEXT,
              text: "还在流式输出",
              status: AgentScopeRuntimeRunStatus.InProgress,
            },
          ],
        },
      ],
    });

    expect(getCompletedReasoningFallbackText(data)).toBe("");
  });

  it("keeps normal assistant body messages as the source of truth", () => {
    const data = response({
      output: [
        {
          id: "reason-1",
          object: "message",
          role: AgentScopeRuntimeMessageRole.ASSISTANT,
          type: AgentScopeRuntimeMessageType.REASONING,
          status: AgentScopeRuntimeRunStatus.Completed,
          content: [
            {
              object: "content",
              type: AgentScopeRuntimeContentType.TEXT,
              text: "模型思考",
              status: AgentScopeRuntimeRunStatus.Completed,
            },
          ],
        },
        {
          id: "message-1",
          object: "message",
          role: AgentScopeRuntimeMessageRole.ASSISTANT,
          type: AgentScopeRuntimeMessageType.MESSAGE,
          status: AgentScopeRuntimeRunStatus.Completed,
          content: [
            {
              object: "content",
              type: AgentScopeRuntimeContentType.TEXT,
              text: "这是正常正文",
              status: AgentScopeRuntimeRunStatus.Completed,
            },
          ],
        },
      ],
    });

    expect(getCompletedReasoningFallbackText(data)).toBe("");
  });
});
