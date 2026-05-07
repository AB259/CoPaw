import TodoList from "@/components/agentscope-chat/OperateCard/preset/TodoList";
import type { ChatTaskProgressData } from "../../taskProgressEvents";

export default function TaskProgressFloatingCard(props: {
  progress: ChatTaskProgressData | null;
}) {
  const { progress } = props;
  if (!progress || progress.phase_status !== "active") {
    return null;
  }

  const description =
    progress.current_step_index !== null
      ? `${progress.current_step_index}/${progress.total_steps}`
      : `${progress.total_steps}`;

  return (
    <div style={{ marginBottom: 12 }}>
      <TodoList
        title={progress.title || "Task Plan"}
        description={description}
        defaultOpen={true}
        list={progress.items.map((item) => ({
          title: item.label,
          status: item.status,
        }))}
      />
    </div>
  );
}
