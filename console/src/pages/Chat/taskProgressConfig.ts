import type { EffectiveSourceSystemConfig } from "@/api/types/sourceSystemConfig";

export function isChatTaskProgressEnabled(
  config: EffectiveSourceSystemConfig | null,
): boolean {
  const rawValue = config?.config?.feature_switches;
  if (!rawValue || typeof rawValue !== "object") {
    return true;
  }
  const enabled = (rawValue as Record<string, unknown>)
    .chat_task_progress_enabled;
  return typeof enabled === "boolean" ? enabled : true;
}
