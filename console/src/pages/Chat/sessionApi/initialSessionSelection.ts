import type { IAgentScopeRuntimeWebUISession } from "@/components/agentscope-chat";
import { resolveRequestedSessionId } from "./resolvedSessionMapping";

interface GetInitialSessionIdOptions {
  pathname: string;
  sessionList: IAgentScopeRuntimeWebUISession[];
}

export function getInitialSessionId({
  pathname,
  sessionList,
}: GetInitialSessionIdOptions): string | undefined {
  const match = pathname.match(/^\/chat\/(.+)$/);
  if (!match?.[1]) {
    return undefined;
  }

  const urlSessionId = match[1];
  return resolveRequestedSessionId({
    requestedSessionId: urlSessionId,
    sessionList,
  });
}
