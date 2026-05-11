import React from "react";
import {
  AgentScopeRuntimeRunStatus,
  IAgentScopeRuntimeMessage,
  IDataContent,
} from "../types";
import { ToolCall } from "@/components/agentscope-chat";
import { useChatAnywhereOptions } from "../../Context/ChatAnywhereOptionsContext";
import Approval from "./Approval";

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  read_file: "读取文件",
  write_file: "写入文件",
  edit_file: "编辑文件",
  append_file: "追加文件",
  execute_shell_command: "执行操作",
  grep_search: "内容搜索",
  glob_search: "文件查找",
  memory_search: "记忆检索",
  browser_use: "网页操作",
  desktop_screenshot: "截取屏幕",
  get_current_time: "获取时间",
  set_user_timezone: "设置时区",
  view_image: "查看图片",
  view_video: "查看视频",
  send_file_to_user: "发送文件",
};

const HIDDEN_TOOL_NAMES = new Set(["update_task_progress"]);
const TOOL_ACTION_NAMES: Record<string, string> = {
  read_file: "读取文件",
  write_file: "写入文件",
  edit_file: "编辑文件",
  append_file: "追加文件",
  grep_search: "搜索内容",
  glob_search: "查找文件",
  memory_search: "检索记忆",
  browser_use: "网页操作",
  view_image: "查看图片",
  view_video: "查看视频",
  send_file_to_user: "发送文件",
};

function getToolDisplayName(toolName?: string, serverLabel?: string) {
  const label = toolName
    ? TOOL_DISPLAY_NAMES[toolName] || toolName
    : "工具操作";
  return serverLabel ? `[${serverLabel}] ${label}` : label;
}

function parseToolArguments(value: unknown): Record<string, any> | null {
  if (!value) return null;
  if (typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, any>;
  }
  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) return null;
  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? parsed
      : null;
  } catch {
    return null;
  }
}

function compactText(value: unknown, maxLength = 64): string {
  if (typeof value !== "string") return "";
  const compacted = value.replace(/\s+/g, " ").trim();
  if (!compacted) return "";
  return compacted.length > maxLength
    ? `${compacted.slice(0, maxLength)}...`
    : compacted;
}

function basename(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  try {
    const url = new URL(trimmed);
    const pathName = url.pathname.split("/").filter(Boolean).pop();
    return decodeURIComponent(pathName || url.hostname || trimmed);
  } catch {
    const segments = trimmed.split(/[\\/]/).filter(Boolean);
    return segments.pop() || trimmed;
  }
}

function getArgumentHint(toolName: string, input: unknown): string {
  const args = parseToolArguments(input);
  if (!args || toolName === "execute_shell_command") return "";

  if (toolName === "browser_use") {
    return compactText(
      args.url || args.text || args.prompt_text || args.action,
    );
  }

  const fileValue =
    args.file_path || args.path || args.filename || args.file_name || args.name;
  if (
    typeof fileValue === "string" &&
    [
      "read_file",
      "write_file",
      "edit_file",
      "append_file",
      "view_image",
      "view_video",
      "send_file_to_user",
    ].includes(toolName)
  ) {
    return compactText(basename(fileValue));
  }

  const commonValue =
    args.query || args.pattern || args.keyword || args.url || args.text;
  return compactText(commonValue);
}

function isUnsafeSummary(summary?: string): boolean {
  if (!summary || summary === "undefined") return true;
  return /[{[\]}]|"[^"]+"\s*:/.test(summary);
}

function buildToolTitle({
  loading,
  toolName,
  defaultTitle,
  input,
  summary,
}: {
  loading: boolean;
  toolName: string;
  defaultTitle: string;
  input: unknown;
  summary?: string;
}): string {
  if (!isUnsafeSummary(summary)) {
    return summary as string;
  }

  const action = TOOL_ACTION_NAMES[toolName] || defaultTitle;
  const hint = getArgumentHint(toolName, input);
  if (hint) {
    return `${loading ? "正在" : ""}${action}：${hint}`;
  }
  return loading ? `正在调用：${defaultTitle}` : `调用工具：${defaultTitle}`;
}

const Tool = React.memo(function ({
  data,
  isApproval = false,
}: {
  data: IAgentScopeRuntimeMessage;
  isApproval?: boolean;
}) {
  const customToolRenderConfig =
    useChatAnywhereOptions((v) => v.customToolRenderConfig) || {};

  if (!data.content?.length) return null;
  const content = data.content as IDataContent<{
    name: string;
    server_label?: string;
    arguments: Record<string, any>;
    output: Record<string, any>;
    summary?: string;
    output_summary?: string;
  }>[];
  const loading = data.status === AgentScopeRuntimeRunStatus.InProgress;
  const toolName = content[0].data.name;
  if (HIDDEN_TOOL_NAMES.has(toolName)) return null;

  const serverLabel = content[0].data.server_label;
  const defaultTitle = getToolDisplayName(toolName, serverLabel);
  const input = content[0]?.data?.arguments;
  const summary = content[0]?.data?.summary;
  const output = content[1]?.data?.output;
  const outputSummary = content[1]?.data?.output_summary;
  const title = buildToolTitle({
    loading,
    toolName,
    defaultTitle,
    input,
    summary,
  });

  let node;

  if (customToolRenderConfig[toolName]) {
    const C = customToolRenderConfig[toolName];
    node = <C data={data} />;
  } else {
    node = (
      <ToolCall
        loading={loading}
        msgStatus={data.status}
        defaultOpen={false}
        title={title}
        input={input}
        output={output}
        outputSummary={outputSummary}
      ></ToolCall>
    );
  }

  return (
    <>
      {node}
      {isApproval && <Approval data={data} />}
    </>
  );
});

export default Tool;
