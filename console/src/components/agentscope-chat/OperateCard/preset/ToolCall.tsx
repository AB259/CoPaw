import { OperateCard, useProviderContext } from "@/components/agentscope-chat";
import {
  SparkCopyLine,
  SparkLoadingLine,
  SparkToolLine,
  SparkTrueLine,
} from "@agentscope-ai/icons";
import { CodeBlock, IconButton } from "@agentscope-ai/design";
import { copy } from "../../Util/copy";
import { useRef, useState } from "react";

function Block(props: {
  title: string;
  content: string | Record<string, any>;
  summary?: string;
  expandEnabled?: boolean;
  defaultExpanded?: boolean;
  language?: "json" | "text";
}) {
  const { getPrefixCls } = useProviderContext();
  const prefixCls = getPrefixCls("operate-card");
  const {
    expandEnabled = false,
    defaultExpanded = true,
    language = "json",
    summary,
  } = props;
  const contentString =
    typeof props.content === "string"
      ? props.content
      : JSON.stringify(props.content);
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(defaultExpanded);
  const timer = useRef<NodeJS.Timeout | null>(null);

  // Show content area when:
  // 1. expanded is true (show full content)
  // 2. OR summary exists and expanded is false (show summary)
  const showContent = expanded || (summary && !expanded);
  const displayContent = summary && !expanded ? summary : contentString;

  return (
    <div className={`${prefixCls}-tool-call-block`}>
      <div
        className={`${prefixCls}-tool-call-block-header`}
        onClick={() => {
          if (expandEnabled === true) {
            setExpanded((prev) => !prev);
          }
        }}
      >
        <span className={`${prefixCls}-tool-call-block-title`}>
          {props.title}
        </span>
        {expandEnabled && summary && (
          <span className={`${prefixCls}-tool-call-block-expand-indicator`}>
            {expanded ? "收起" : "展开详情"}
          </span>
        )}
        <div
          className={`${prefixCls}-tool-call-block-extra`}
          onClick={(e) => e.stopPropagation()}
        >
          <IconButton
            size="small"
            style={{ marginRight: "-6px" }}
            icon={copied ? <SparkTrueLine /> : <SparkCopyLine />}
            bordered={false}
            onClick={() => {
              copy(contentString)
                .then(() => {
                  clearTimeout(timer.current);
                  setCopied(true);
                  timer.current = setTimeout(() => {
                    setCopied(false);
                  }, 2000);
                })
                .catch(() => {
                  console.warn("Copy failed");
                });
            }}
          />
        </div>
      </div>
      {showContent && (
        <div className={`${prefixCls}-tool-call-block-content`}>
          {/* @ts-ignore */}
          <CodeBlock
            language={language}
            value={displayContent}
            readOnly={true}
            basicSetup={{ lineNumbers: false, foldGutter: false }}
          />
        </div>
      )}
    </div>
  );
}

export interface IToolCallProps {
  /**
   * @description 标题
   * @descriptionEn Title
   * @default 'Call Tool'
   */
  title?: string;
  /**
   * @description 副标题
   * @descriptionEn Subtitle
   * @default ''
   */
  subTitle?: string;
  /**
   * @description 工具调用入参
   * @descriptionEn Tool Call Input
   * @default ''
   */
  input: string | Record<string, any>;
  /**
   * @description 工具调用输出
   * @descriptionEn Tool Call Output
   * @default ''
   */
  output: string | Record<string, any>;
  /**
   * @description 输出摘要
   * @descriptionEn Output Summary
   */
  outputSummary?: string;
  /**
   * @description 默认展开
   * @descriptionEn Default Open
   */
  defaultOpen?: boolean;
  /**
   * @description 是否正在生成
   * @descriptionEn Whether is generating
   * @default false
   */
  loading?: boolean;

  outputBlock?: { language?: "json" | "text" };
  inputBlock?: { language?: "json" | "text" };
}

export default function (props: IToolCallProps) {
  const {
    title = "Call Tool",
    subTitle,
    defaultOpen = true,
    loading = false,
    outputSummary,
  } = props;

  return (
    <OperateCard
      header={{
        icon: loading ? <SparkLoadingLine spin /> : <SparkToolLine />,
        title: title,
        description: subTitle,
      }}
      body={{
        defaultOpen: defaultOpen,
        children: (
          <OperateCard.LineBody>
            <Block
              title="输入"
              content={props.input}
              language={props.inputBlock?.language}
              expandEnabled={true}
              defaultExpanded={true}
            />
            <Block
              title="输出"
              content={props.output}
              summary={outputSummary}
              language={props.outputBlock?.language}
              expandEnabled={!!outputSummary}
              defaultExpanded={!outputSummary}
            />
          </OperateCard.LineBody>
        ),
      }}
    ></OperateCard>
  );
}
