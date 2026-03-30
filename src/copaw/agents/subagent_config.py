# -*- coding: utf-8 -*-
"""Sub-Agent Configuration.

This module defines configuration classes and type definitions for sub-agents.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SubAgentConfig(BaseModel):
    """Configuration for creating a sub-agent.

    Attributes:
        agent_type: Type of sub-agent to create (e.g., "general-purpose", "file-searcher")
        description: Optional description of this sub-agent's purpose
        model_id: Override model ID for this sub-agent (None = use parent's model)
        provider_id: Override provider ID for this sub-agent (None = use parent's provider)
        enable_memory: Whether to enable memory management for sub-agent
        enable_mcp: Whether to enable MCP clients for sub-agent
        max_iters: Maximum number of reasoning iterations (default: 50)
        timeout: Maximum execution time in seconds (default: 300s = 5 min)
        parent_id: Parent agent ID for tracking
    """

    agent_type: str = "general-purpose"
    description: Optional[str] = None
    model_id: Optional[str] = None
    provider_id: Optional[str] = None
    enable_memory: bool = False
    enable_mcp: bool = False
    max_iters: int = 50
    timeout: int = 300
    parent_id: Optional[str] = None
    system_prompt_override: Optional[str] = None


# Predefined sub-agent type configurations
SUBAGENT_TYPES: Dict[str, Dict[str, Any]] = {
    "general-purpose": {
        "description": "Standard agent with all tools and capabilities",
        "system_prompt_suffix": "",
        "tool_filter": None,  # All tools
        "enable_memory_default": True,
        "enable_mcp_default": True,
    },
    "file-searcher": {
        "description": "Specialized for file operations and searching",
        "system_prompt_suffix": """
You are a file search specialist. Focus on:
- Efficient file discovery using glob and grep patterns
- Reading relevant file contents with context
- Summarizing file structures and dependencies
Avoid executing shell commands unless explicitly required.
""",
        "tool_filter": [
            "read_file",
            "write_file",
            "grep_search",
            "glob_search",
            "edit_file",
        ],
        "enable_memory_default": False,
        "enable_mcp_default": False,
    },
    "code-reviewer": {
        "description": "Specialized for code analysis and review",
        "system_prompt_suffix": """
You are a code review specialist. Focus on:
- Analyzing code quality and patterns
- Identifying potential bugs and issues
- Suggesting improvements
- Reviewing code for best practices
""",
        "tool_filter": [
            "read_file",
            "grep_search",
            "glob_search",
        ],
        "enable_memory_default": True,
        "enable_mcp_default": False,
    },
    "planner": {
        "description": "Specialized for task planning and breakdown",
        "system_prompt_suffix": """
You are a planning specialist. Focus on:
- Breaking down complex tasks into steps
- Identifying dependencies and ordering
- Creating clear, actionable plans
- Estimating complexity and resources needed
Avoid executing operations; focus on planning.
""",
        "tool_filter": [
            "read_file",
            "grep_search",
            "glob_search",
        ],
        "enable_memory_default": False,
        "enable_mcp_default": False,
    },
}


def get_subagent_type_config(agent_type: str) -> Dict[str, Any]:
    """Get configuration for a specific sub-agent type.

    Args:
        agent_type: The type of sub-agent

    Returns:
        Configuration dictionary for the agent type, or defaults
    """
    return SUBAGENT_TYPES.get(agent_type, SUBAGENT_TYPES["general-purpose"])


def is_valid_subagent_type(agent_type: str) -> bool:
    """Check if an agent type is valid.

    Args:
        agent_type: The agent type to check

    Returns:
        True if the agent type is defined, False otherwise
    """
    return agent_type in SUBAGENT_TYPES


def list_subagent_types() -> List[str]:
    """List all available sub-agent types.

    Returns:
        List of sub-agent type names
    """
    return list(SUBAGENT_TYPES.keys())
