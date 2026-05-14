import {
  AgentScopeRuntimeContentType,
  AgentScopeRuntimeMessageType,
  AgentScopeRuntimeRunStatus,
  IAgentScopeRuntimeMessage,
  IAgentScopeRuntimeResponse,
} from "../types";

function hasVisibleMessageContent(message: IAgentScopeRuntimeMessage) {
  if (message.type !== AgentScopeRuntimeMessageType.MESSAGE) {
    return false;
  }

  return Boolean(
    message.content?.some((content) => {
      switch (content.type) {
        case AgentScopeRuntimeContentType.TEXT:
          return Boolean(content.text?.trim());
        case AgentScopeRuntimeContentType.REFUSAL:
          return Boolean(content.refusal?.trim());
        case AgentScopeRuntimeContentType.IMAGE:
          return Boolean(content.image_url);
        case AgentScopeRuntimeContentType.VIDEO:
          return Boolean(content.video_url);
        case AgentScopeRuntimeContentType.FILE:
          return Boolean(
            content.file_url || content.file_name || content.fileName,
          );
        case AgentScopeRuntimeContentType.AUDIO:
          return Boolean(content.audio_url || content.data);
        case AgentScopeRuntimeContentType.DATA:
          return Boolean(content.data);
        default:
          return false;
      }
    }),
  );
}

function getReasoningText(message: IAgentScopeRuntimeMessage) {
  if (message.type !== AgentScopeRuntimeMessageType.REASONING) {
    return "";
  }

  return (
    message.content
      ?.filter((content) => content.type === AgentScopeRuntimeContentType.TEXT)
      .map((content) => content.text?.trim())
      .filter(Boolean)
      .join("\n\n") || ""
  );
}

export function getCompletedReasoningFallbackText(
  response: IAgentScopeRuntimeResponse,
  messages: IAgentScopeRuntimeMessage[] = response.output,
) {
  if (response.status !== AgentScopeRuntimeRunStatus.Completed) {
    return "";
  }

  if (messages.some(hasVisibleMessageContent)) {
    return "";
  }

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const text = getReasoningText(messages[index]);
    if (text) {
      return text;
    }
  }

  return "";
}
