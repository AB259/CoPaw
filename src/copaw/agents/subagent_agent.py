# -*- coding: utf-8 -*-
"""Sub-agent CoPaw agent helpers."""
from typing import Any, List, Optional

from agentscope.tool import Toolkit

from .react_agent import CoPawAgent, NamesakeStrategy
from .skills_manager import get_working_skills_dir, list_available_skills
from .tools.browser_control import browser_use
from .tools.desktop_screenshot import desktop_screenshot
from .tools.file_io import edit_file, read_file, write_file
from .tools.file_search import grep_search, glob_search
from .tools.get_current_time import get_current_time
from .tools.send_file import send_file_to_user
from .tools.shell import execute_shell_command


class SubAgentCoPawAgent(CoPawAgent):
    """CoPawAgent variant with optional tool filtering and prompt override."""

    def __init__(
        self,
        env_context: Optional[str] = None,
        enable_memory_manager: bool = False,
        mcp_clients: Optional[List[Any]] = None,
        memory_manager: Any | None = None,
        max_iters: int = 50,
        max_input_length: int = 128 * 1024,
        namesake_strategy: NamesakeStrategy = "skip",
        parent_agent: Optional[CoPawAgent] = None,
        tool_filter: Optional[List[str]] = None,
        system_prompt_override: Optional[str] = None,
    ):
        super().__init__(
            env_context=env_context,
            enable_memory_manager=enable_memory_manager,
            mcp_clients=mcp_clients,
            memory_manager=memory_manager,
            max_iters=max_iters,
            max_input_length=max_input_length,
            namesake_strategy=namesake_strategy,
        )

        self._parent_agent = parent_agent
        self._tool_filter = tool_filter
        self._system_prompt_override = system_prompt_override

        if parent_agent is not None:
            self.model = parent_agent.model
            self.formatter = parent_agent.formatter
            if self._enable_memory_manager and self.memory_manager is not None:
                self.memory_manager.chat_model = self.model
                self.memory_manager.formatter = self.formatter

        if tool_filter is not None:
            self.toolkit = self._create_filtered_toolkit(
                tool_filter=tool_filter,
                namesake_strategy=namesake_strategy,
            )

        if system_prompt_override:
            self._sys_prompt = self._build_sys_prompt_with_override(
                override=system_prompt_override,
            )
            for msg, _marks in self.memory.content:
                if msg.role == "system":
                    msg.content = self.sys_prompt
                    break

    def _create_filtered_toolkit(
        self,
        tool_filter: Optional[List[str]] = None,
        namesake_strategy: NamesakeStrategy = "skip",
    ) -> Toolkit:
        """Create toolkit with only specified tools."""
        if tool_filter is None:
            return self._create_toolkit(namesake_strategy)

        toolkit = Toolkit()
        tool_functions = {
            "execute_shell_command": execute_shell_command,
            "read_file": read_file,
            "write_file": write_file,
            "edit_file": edit_file,
            "browser_use": browser_use,
            "desktop_screenshot": desktop_screenshot,
            "send_file_to_user": send_file_to_user,
            "get_current_time": get_current_time,
            "grep_search": grep_search,
            "glob_search": glob_search,
        }

        for tool_name in tool_filter:
            tool_func = tool_functions.get(tool_name)
            if tool_func is None:
                continue
            toolkit.register_tool_function(
                tool_func,
                namesake_strategy=namesake_strategy,
            )

        return toolkit

    def _create_toolkit(
        self,
        namesake_strategy: NamesakeStrategy = "skip",
    ) -> Toolkit:
        """Create toolkit with all supported sub-agent tools."""
        from .tools.memory_search import create_memory_search_tool

        toolkit = Toolkit()
        tool_functions = {
            "execute_shell_command": execute_shell_command,
            "read_file": read_file,
            "write_file": write_file,
            "edit_file": edit_file,
            "browser_use": browser_use,
            "desktop_screenshot": desktop_screenshot,
            "send_file_to_user": send_file_to_user,
            "get_current_time": get_current_time,
            "grep_search": grep_search,
            "glob_search": glob_search,
        }

        try:
            from ..config import load_config

            config = load_config()
            enabled_tools = (
                config.tools.builtin_tools
                if hasattr(config, "tools")
                and hasattr(config.tools, "builtin_tools")
                else {}
            )
        except Exception:
            enabled_tools = {}

        for tool_name, tool_func in tool_functions.items():
            if enabled_tools.get(tool_name, True):
                toolkit.register_tool_function(
                    tool_func,
                    namesake_strategy=namesake_strategy,
                )

        memory_manager = getattr(self, "memory_manager", None)
        if memory_manager is not None:
            toolkit.register_tool_function(
                create_memory_search_tool(memory_manager),
                namesake_strategy=namesake_strategy,
            )

        return toolkit

    @staticmethod
    def _register_skills_on_toolkit(toolkit: Toolkit) -> None:
        """Register working-directory skills on an arbitrary toolkit."""
        working_skills_dir = get_working_skills_dir()
        for skill_name in list_available_skills():
            skill_dir = working_skills_dir / skill_name
            if skill_dir.exists():
                toolkit.register_agent_skill(str(skill_dir))

    def _build_sys_prompt_with_override(
        self,
        override: Optional[str] = None,
    ) -> str:
        """Build system prompt with optional override text appended."""
        from .prompt import build_system_prompt_from_working_dir

        base_prompt = build_system_prompt_from_working_dir()
        if override:
            return f"{base_prompt}\n\n{override}"
        return base_prompt


def create_subagent(
    config: Any,
    parent_agent: Optional[CoPawAgent] = None,
    mcp_clients: Optional[List[Any]] = None,
    memory_manager: Any | None = None,
) -> CoPawAgent:
    """Factory function to create configured sub-agents."""
    from .subagent_config import get_subagent_type_config

    type_config = get_subagent_type_config(config.agent_type)
    system_suffix = type_config.get("system_prompt_suffix", "")
    tool_filter = type_config.get("tool_filter")
    system_prompt_override = config.system_prompt_override or system_suffix

    enable_memory = config.enable_memory
    enable_mcp = config.enable_mcp

    if parent_agent is not None:
        if mcp_clients is None and hasattr(parent_agent, "_mcp_clients"):
            mcp_clients = parent_agent._mcp_clients if enable_mcp else []
        if memory_manager is None and hasattr(parent_agent, "memory_manager"):
            memory_manager = (
                parent_agent.memory_manager if enable_memory else None
            )

    return SubAgentCoPawAgent(
        env_context=f"Sub-agent: {config.description or config.agent_type}",
        enable_memory_manager=enable_memory,
        mcp_clients=mcp_clients,
        memory_manager=memory_manager,
        max_iters=config.max_iters,
        namesake_strategy="skip",
        parent_agent=parent_agent,
        tool_filter=tool_filter,
        system_prompt_override=system_prompt_override,
    )
