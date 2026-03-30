# -*- coding: utf-8 -*-
"""Sub-Agent Tool.

This module provides the agent() tool for creating and executing sub-agents.
"""
import logging
from typing import Any, Optional

from agentscope.tool import ToolResponse
from pydantic import BaseModel

from agentscope.message import TextBlock

from ..subagent_config import (
    SubAgentConfig,
    is_valid_subagent_type,
    list_subagent_types,
)
from ..subagent_manager import SubAgentManager

logger = logging.getLogger(__name__)

# Global reference to parent agent for creating sub-agents
_parent_agent: Optional[Any] = None


def set_parent_agent(agent: Any) -> None:
    """Set the parent agent reference.

    Args:
        agent: The parent CoPawAgent instance
    """
    global _parent_agent
    _parent_agent = agent


async def agent(
    prompt: str,
    subagent_type: str = "general-purpose",
    description: Optional[str] = None,
    model_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    enable_memory: bool = False,
    enable_mcp: bool = False,
    timeout: int = 300,
    run_in_background: bool = False,
) -> ToolResponse:
    """Create and execute a sub-agent to handle a specific task.

    This tool allows the main agent to delegate tasks to specialized
    sub-agents with different configurations and toolsets.

    Args:
        prompt (`str`): The task description/instruction for the sub-agent.
        subagent_type (`str`, optional): Type of sub-agent to create. Options:
            - "general-purpose": Standard agent with all tools
            - "file-searcher": Agent specialized for file operations
            - "code-reviewer": Agent specialized for code analysis
            - "planner": Agent for planning and task breakdown
            Defaults to "general-purpose".
        description (`Optional[str]`, optional): Optional description of this
            sub-agent's purpose. Defaults to None.
        model_id (`Optional[str]`, optional): Override model for this sub-agent.
            None = use parent's model. Defaults to None.
        provider_id (`Optional[str]`, optional): Override provider for this sub-agent.
            None = use parent's provider. Defaults to None.
        enable_memory (`bool`, optional): Whether to enable memory management
            for sub-agent. Defaults to False.
        enable_mcp (`bool`, optional): Whether to enable MCP clients for sub-agent.
            Defaults to False.
        timeout (`int`, optional): Maximum execution time in seconds.
            Defaults to 300 (5 minutes).
        run_in_background (`bool`, optional): If True, returns immediately with
            a task_id. Defaults to False.

    Returns:
        `ToolResponse`: If run_in_background=False, contains task completion result.
            If run_in_background=True, contains task_id and status info.

    Examples:
        Synchronous execution:
        ```python
        agent(
            prompt="Analyze the code in src/ directory",
            subagent_type="code-reviewer",
            timeout=300
        )
        ```

        Background execution:
        ```python
        agent(
            prompt="Perform full codebase audit",
            subagent_type="general-purpose",
            run_in_background=True
        )
        # Returns: Task ID: agent_abc123
        ```
    """
    global _parent_agent

    # Validate subagent_type
    if not is_valid_subagent_type(subagent_type):
        available_types = ", ".join(list_subagent_types())
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error: Invalid subagent_type '{subagent_type}'. "
                    f"Available types: {available_types}",
                )
            ]
        )

    # Check timeout limit
    max_timeout = 600  # 10 minutes
    if timeout > max_timeout:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error: Timeout {timeout}s exceeds maximum "
                    f"allowed {max_timeout}s.",
                )
            ]
        )

    # Create configuration
    config = SubAgentConfig(
        agent_type=subagent_type,
        description=description,
        model_id=model_id,
        provider_id=provider_id,
        enable_memory=enable_memory,
        enable_mcp=enable_mcp,
        timeout=timeout,
        parent_id=get_parent_agent_id(),
    )

    # Create sub-agent instance
    try:
        from ..subagent_agent import create_subagent

        subagent = create_subagent(
            config=config,
            parent_agent=_parent_agent,
        )
    except Exception as e:
        logger.exception(f"Failed to create sub-agent: {e}")
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Failed to create sub-agent: {str(e)}",
                )
            ]
        )

    # Register with manager
    manager = SubAgentManager.get_instance()
    try:
        agent_id = await manager.create_agent(
            config=config,
            agent_instance=subagent,
        )
    except ValueError as e:
        return ToolResponse(
            content=[TextBlock(type="text", text=str(e))]
        )
    except Exception as e:
        logger.exception(f"Failed to register sub-agent: {e}")
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Failed to register sub-agent: {str(e)}",
                )
            ]
        )

    # Execute
    logger.info(f"Executing sub-agent: {agent_id}")
    result = await manager.execute_agent(
        agent_id=agent_id,
        prompt=prompt,
        run_in_background=run_in_background,
    )

    return result


def get_parent_agent_id() -> Optional[str]:
    """Get the parent agent ID.

    Returns:
        Parent agent ID if available, None otherwise
    """
    global _parent_agent
    if _parent_agent is None:
        return None

    if hasattr(_parent_agent, "name"):
        return _parent_agent.name
    elif hasattr(_parent_agent, "id"):
        return str(_parent_agent.id)
    else:
        return None
