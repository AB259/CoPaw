import AgentScopeRuntimeResponseCard from "@/components/agentscope-chat/AgentScopeRuntimeWebUI/core/AgentScopeRuntime/Response/Card";
import { useIframeStore } from "@/stores/iframeStore";
import ChatMessageMeta from "../ChatMessageMeta";
import type { ChatRuntimeResponseCardData } from "../../messageMeta";
import styles from "../ChatMessageMeta/index.module.less";

const ASSISTANT_MESSAGE_NAME = "小助 Claw";
const ORIGIN_Y_ASSISTANT_MESSAGE_NAME = "AI伙伴";
const ORIGIN_Y_SOURCE = "RMASSIST";

type AssistantMessageContext = {
  hideMenu?: boolean;
  source?: string | null;
};

export function getAssistantMessageName(
  search: string = window.location.search,
  context?: AssistantMessageContext,
): string {
  const urlParams = new URLSearchParams(search);
  const isOriginYContext =
    context?.hideMenu === true && context?.source === ORIGIN_Y_SOURCE;
  return urlParams.get("origin") === "Y" || isOriginYContext
    ? ORIGIN_Y_ASSISTANT_MESSAGE_NAME
    : ASSISTANT_MESSAGE_NAME;
}

export default function RuntimeResponseCard(props: {
  data: ChatRuntimeResponseCardData;
  isLast?: boolean;
}) {
  const hideMenu = useIframeStore((state) => state.hideMenu);
  const source = useIframeStore((state) => state.source);

  return (
    <div className={styles.messageBlockStart}>
      <ChatMessageMeta
        align="start"
        name={getAssistantMessageName(window.location.search, {
          hideMenu,
          source,
        })}
        timestamp={props.data.headerMeta?.timestamp}
      />
      <AgentScopeRuntimeResponseCard data={props.data} isLast={props.isLast} />
    </div>
  );
}
