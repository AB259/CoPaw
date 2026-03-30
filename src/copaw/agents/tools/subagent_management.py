# -*- coding: utf-8 -*-
"""Sub-agent management tools."""
import json
import logging
from typing import Optional

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from ..subagent_manager import SubAgentManager

logger = logging.getLogger(__name__)

_STATUS_LABELS = {
    "created": "[created]",
    "running": "[running]",
    "completed": "[completed]",
    "failed": "[failed]",
    "cancelled": "[cancelled]",
}


async def list_agents(parent_id: Optional[str] = None) -> ToolResponse:
    """List all active sub-agents."""
    manager = SubAgentManager.get_instance()

    try:
        agents_list = await manager.list_agents(parent_id=parent_id)
        if not agents_list:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="No active sub-agents found.",
                    )
                ]
            )

        output_lines = ["Active Sub-Agents:", "-" * 80]
        for agent_info in agents_list:
            status_label = _STATUS_LABELS.get(
                agent_info["status"],
                "[unknown]",
            )
            output_lines.append(f"\n{status_label} {agent_info['agent_id']}")
            output_lines.append(f"  Type: {agent_info['type']}")
            if agent_info.get("description"):
                output_lines.append(
                    f"  Description: {agent_info['description']}"
                )
            output_lines.append(f"  Status: {agent_info['status']}")
            if agent_info.get("started_at"):
                output_lines.append(
                    f"  Started: {_format_timestamp(agent_info['started_at'])}"
                )
            if agent_info.get("duration") is not None:
                output_lines.append(
                    f"  Duration: {agent_info['duration']:.2f} seconds"
                )
            if agent_info.get("error"):
                output_lines.append(f"  Error: {agent_info['error']}")

        output_lines.append("\n" + "-" * 80)
        output_lines.append(f"Total: {len(agents_list)} sub-agent(s)")

        return ToolResponse(
            content=[
                TextBlock(type="text", text="\n".join(output_lines)),
                TextBlock(
                    type="text",
                    text=(
                        "\n\nFull data:\n```json\n"
                        f"{json.dumps(agents_list, indent=2)}\n```"
                    ),
                ),
            ]
        )
    except Exception as exc:
        logger.exception("Failed to list agents: %s", exc)
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error listing agents: {exc}",
                )
            ]
        )


async def get_agent_status(agent_id: str) -> ToolResponse:
    """Get detailed status of a specific sub-agent."""
    manager = SubAgentManager.get_instance()

    try:
        status = await manager.get_agent_status(agent_id=agent_id)
        if status.get("status") == "not_found":
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error: Agent ID '{agent_id}' not found.",
                    )
                ]
            )

        status_label = _STATUS_LABELS.get(status["status"], "[unknown]")
        output_lines = [
            f"Sub-Agent Status: {agent_id}",
            "-" * 80,
            f"\nStatus: {status_label} {status['status']}",
            f"Type: {status['type']}",
        ]

        if status.get("description"):
            output_lines.append(f"Description: {status['description']}")
        output_lines.append(
            f"Created: {_format_timestamp(status['created_at'])}"
        )
        if status.get("started_at"):
            output_lines.append(
                f"Started: {_format_timestamp(status['started_at'])}"
            )
        if status.get("completed_at"):
            output_lines.append(
                f"Completed: {_format_timestamp(status['completed_at'])}"
            )
        if status.get("duration") is not None:
            output_lines.append(
                f"Duration: {status['duration']:.2f} seconds"
            )
        if status.get("error"):
            output_lines.append(f"Error: {status['error']}")
        if status.get("has_result"):
            output_lines.append("Result: Available (use agent output)")

        return ToolResponse(
            content=[
                TextBlock(type="text", text="\n".join(output_lines)),
                TextBlock(
                    type="text",
                    text=(
                        "\n\nFull data:\n```json\n"
                        f"{json.dumps(status, indent=2)}\n```"
                    ),
                ),
            ]
        )
    except Exception as exc:
        logger.exception("Failed to get agent status: %s", exc)
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error getting agent status: {exc}",
                )
            ]
        )


async def cancel_agent(agent_id: str) -> ToolResponse:
    """Cancel a running sub-agent."""
    manager = SubAgentManager.get_instance()

    try:
        success = await manager.cancel_agent(agent_id=agent_id)
        if success:
            message = f"Agent '{agent_id}' cancelled successfully."
        else:
            message = (
                f"Failed to cancel agent '{agent_id}'. "
                "The agent may not be running or does not exist."
            )
        return ToolResponse(content=[TextBlock(type="text", text=message)])
    except Exception as exc:
        logger.exception("Failed to cancel agent: %s", exc)
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error cancelling agent: {exc}",
                )
            ]
        )


def _format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp to readable string."""
    import datetime

    return datetime.datetime.fromtimestamp(timestamp).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
