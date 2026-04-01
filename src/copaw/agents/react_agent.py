# -*- coding: utf-8 -*-
"""CoPaw Agent - Main agent implementation.

This module provides the main CoPawAgent class built on ReActAgent,
with integrated tools, skills, and memory management.
"""
import asyncio
import logging
import os
from typing import Any, List, Literal, Optional, Type

from agentscope.agent import ReActAgent
from agentscope.mcp import HttpStatefulClient, StdIOStatefulClient
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.tool import Toolkit
from anyio import ClosedResourceError
from pydantic import BaseModel

from .command_handler import CommandHandler
from .hooks import BootstrapHook, MemoryCompactionHook
from .model_factory import create_model_and_formatter
from .prompt import build_system_prompt_from_working_dir
from .skills_manager import (
    ensure_skills_initialized,
    get_working_skills_dir,
    list_available_skills,
)
from .tools.browser_control import browser_use
from .tools.desktop_screenshot import desktop_screenshot
from .tools.file_io import edit_file, read_file, write_file
from .tools.get_current_time import get_current_time
from .tools.memory_search import create_memory_search_tool
from .tools.send_file import send_file_to_user
from .tools.shell import execute_shell_command
from .tools.subagent import agent, set_parent_agent
from .tools.subagent_management import (
    cancel_agent,
    get_agent_status,
    list_agents,
)
from .utils import process_file_and_media_blocks_in_message
from ..agents.memory import MemoryManager
from ..config import load_config
from ..constant import (
    MEMORY_COMPACT_KEEP_RECENT,
    MEMORY_COMPACT_RATIO,
    get_request_working_dir,
)

logger = logging.getLogger(__name__)

# Valid namesake strategies for tool registration
NamesakeStrategy = Literal["override", "skip", "raise", "rename"]


def normalize_reasoning_tool_choice(
    tool_choice: Literal["auto", "none", "required"] | None,
    has_tools: bool,
) -> Literal["auto", "none", "required"] | None:
    """Normalize tool_choice for reasoning to reduce provider variance."""
    if tool_choice is None and has_tools:
        return "auto"
    return tool_choice


class CoPawAgent(ReActAgent):
    """CoPaw Agent with integrated tools, skills, and memory management.

    This agent extends ReActAgent with:
    - Built-in tools (shell, file operations, browser, etc.)
    - Dynamic skill loading from working directory
    - Memory management with auto-compaction
    - Bootstrap guidance for first-time setup
    - System command handling (/compact, /new, etc.)
    - Optional tracing for analytics
    """

    def __init__(
        self,
        env_context: Optional[str] = None,
        enable_memory_manager: bool = True,
        enable_tracing: bool = False,
        mcp_clients: Optional[List[Any]] = None,
        memory_manager: MemoryManager | None = None,
        max_iters: int = 50,
        max_input_length: int = 128 * 1024,  # 128K = 131072 tokens
        namesake_strategy: NamesakeStrategy = "skip",
        trace_id: Optional[str] = None,
    ):
        """Initialize CoPawAgent.

        Args:
            env_context: Optional environment context to prepend to
                system prompt
            enable_memory_manager: Whether to enable memory manager
            enable_tracing: Whether to enable tracing for analytics
            mcp_clients: Optional list of MCP clients for tool
                integration
            memory_manager: Optional memory manager instance
            max_iters: Maximum number of reasoning-acting iterations
                (default: 50)
            max_input_length: Maximum input length in tokens for model
                context window (default: 128K = 131072)
            namesake_strategy: Strategy to handle namesake tool functions.
                Options: "override", "skip", "raise", "rename"
                (default: "skip")
            trace_id: Optional trace ID for linking tracing events
        """
        self._env_context = env_context
        self._max_input_length = max_input_length
        self._mcp_clients = mcp_clients or []
        self._mcp_tool_to_server: dict[str, str] = {}  # tool_name -> mcp_server_name
        self._namesake_strategy = namesake_strategy
        self._enable_tracing = enable_tracing
        self._trace_id = trace_id

        # Memory compaction threshold: configurable ratio of max_input_length
        self._memory_compact_threshold = int(
            max_input_length * MEMORY_COMPACT_RATIO,
        )

        # Initialize toolkit with built-in tools
        toolkit = self._create_toolkit(namesake_strategy=namesake_strategy)

        # Load and register skills
        self._register_skills(toolkit)

        # Build system prompt
        sys_prompt = self._build_sys_prompt()

        # Create model and formatter using factory method
        model, formatter = create_model_and_formatter()

        # Initialize parent ReActAgent
        super().__init__(
            name="Friday",
            model=model,
            sys_prompt=sys_prompt,
            toolkit=toolkit,
            memory=InMemoryMemory(),
            formatter=formatter,
            max_iters=max_iters,
        )

        # Setup memory manager
        self._setup_memory_manager(
            enable_memory_manager,
            memory_manager,
            namesake_strategy,
        )

        # Setup command handler
        self.command_handler = CommandHandler(
            agent_name=self.name,
            memory=self.memory,
            memory_manager=self.memory_manager,
            enable_memory_manager=self._enable_memory_manager,
        )

        # Register hooks
        self._register_hooks()

        # Set as parent agent for sub-agents
        set_parent_agent(self)

    def _create_toolkit(
        self,
        namesake_strategy: NamesakeStrategy = "skip",
    ) -> Toolkit:
        """Create and populate toolkit with built-in tools.

        Args:
            namesake_strategy: Strategy to handle namesake tool functions.
                Options: "override", "skip", "raise", "rename"
                (default: "skip")

        Returns:
            Configured toolkit instance
        """
        toolkit = Toolkit()

        # Register built-in tools
        toolkit.register_tool_function(
            execute_shell_command,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            read_file,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            write_file,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            edit_file,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            browser_use,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            desktop_screenshot,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            send_file_to_user,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            get_current_time,
            namesake_strategy=namesake_strategy,
        )
        # Register sub-agent tools
        toolkit.register_tool_function(
            agent,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            list_agents,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            get_agent_status,
            namesake_strategy=namesake_strategy,
        )
        toolkit.register_tool_function(
            cancel_agent,
            namesake_strategy=namesake_strategy,
        )

        return toolkit

    def _register_skills(self, toolkit: Toolkit) -> None:
        """Load and register skills from working directory.

        Args:
            toolkit: Toolkit to register skills to
        """
        # Check skills initialization
        ensure_skills_initialized()

        working_skills_dir = get_working_skills_dir()
        available_skills = list_available_skills()

        # Store registered skill names for tracing distinction
        self._registered_skills: set[str] = set()

        for skill_name in available_skills:
            skill_dir = working_skills_dir / skill_name
            if skill_dir.exists():
                try:
                    toolkit.register_agent_skill(str(skill_dir))
                    logger.debug("Registered skill directory: %s", skill_name)
                except Exception as e:
                    logger.error(
                        "Failed to register skill '%s': %s",
                        skill_name,
                        e,
                    )

        # Get actual skill names from toolkit.skills (set by register_agent_skill)
        # The skill name comes from SKILL.md YAML front matter, not directory name
        self._registered_skills = set(toolkit.skills.keys())
        logger.debug("Registered skills for tracing: %s (from %d available skill dirs)",
                    self._registered_skills, len(available_skills))

    def _build_sys_prompt(self) -> str:
        """Build system prompt from working dir files and env context.

        Returns:
            Complete system prompt string
        """
        sys_prompt = build_system_prompt_from_working_dir()
        if self._env_context is not None:
            sys_prompt = self._env_context + "\n\n" + sys_prompt
        return sys_prompt

    def _setup_memory_manager(
        self,
        enable_memory_manager: bool,
        memory_manager: MemoryManager | None,
        namesake_strategy: NamesakeStrategy,
    ) -> None:
        """Setup memory manager and register memory search tool if enabled.

        Args:
            enable_memory_manager: Whether to enable memory manager
            memory_manager: Optional memory manager instance
            namesake_strategy: Strategy to handle namesake tool functions
        """
        # Check env var: if ENABLE_MEMORY_MANAGER=false, disable memory manager
        env_enable_mm = os.getenv("ENABLE_MEMORY_MANAGER", "")
        if env_enable_mm.lower() == "false":
            enable_memory_manager = False

        self._enable_memory_manager: bool = enable_memory_manager
        self.memory_manager = memory_manager

        # Register memory_search tool if enabled and available
        if self._enable_memory_manager and self.memory_manager is not None:
            # update memory manager
            self.memory_manager.chat_model = self.model
            self.memory_manager.formatter = self.formatter
            memory_toolkit = Toolkit()
            memory_toolkit.register_tool_function(
                read_file,
                namesake_strategy=self._namesake_strategy,
            )
            memory_toolkit.register_tool_function(
                write_file,
                namesake_strategy=self._namesake_strategy,
            )
            memory_toolkit.register_tool_function(
                edit_file,
                namesake_strategy=self._namesake_strategy,
            )
            self.memory_manager.toolkit = memory_toolkit
            self.memory_manager.update_config_params()

            self.memory = self.memory_manager.get_in_memory_memory()

            # Register memory_search as a tool function
            self.toolkit.register_tool_function(
                create_memory_search_tool(self.memory_manager),
                namesake_strategy=namesake_strategy,
            )
            logger.debug("Registered memory_search tool")

    def _register_hooks(self) -> None:
        """Register pre-reasoning hooks for bootstrap and memory compaction."""
        # Bootstrap hook - checks BOOTSTRAP.md on first interaction
        config = load_config()
        bootstrap_hook = BootstrapHook(
            working_dir=get_request_working_dir(),  # Use request-scoped
            language=config.agents.language,
        )
        self.register_instance_hook(
            hook_type="pre_reasoning",
            hook_name="bootstrap_hook",
            hook=bootstrap_hook.__call__,
        )
        logger.debug("Registered bootstrap hook")

        # Memory compaction hook - auto-compact when context is full
        if self._enable_memory_manager and self.memory_manager is not None:
            memory_compact_hook = MemoryCompactionHook(
                memory_manager=self.memory_manager,
                memory_compact_threshold=self._memory_compact_threshold,
                keep_recent=MEMORY_COMPACT_KEEP_RECENT,
            )
            self.register_instance_hook(
                hook_type="pre_reasoning",
                hook_name="memory_compact_hook",
                hook=memory_compact_hook.__call__,
            )
            logger.debug("Registered memory compaction hook")

        # Tracing hook - emit tracing events during reasoning (if enabled)
        if self._enable_tracing and self._trace_id:
            self._register_tracing_hooks()

    def _register_tracing_hooks(self) -> None:
        """Register tracing hooks for the agent."""
        try:
            from .hooks import TracingHook, TracingHookRegistry

            # Get user context from env_context
            # Format: "- 当前的user_id: xxx" or "user_id: xxx"
            user_id = ""
            session_id = ""
            channel = ""
            if self._env_context:
                for line in self._env_context.split("\n"):
                    # Support both formats: "user_id: xxx" and "- 当前的user_id: xxx"
                    if "user_id" in line.lower() and "session_id" not in line.lower():
                        # Extract value after the last colon
                        if ":" in line:
                            user_id = line.rsplit(":", 1)[1].strip()
                    elif "session_id" in line.lower():
                        if ":" in line:
                            session_id = line.rsplit(":", 1)[1].strip()
                    elif "channel" in line.lower():
                        if ":" in line:
                            channel = line.rsplit(":", 1)[1].strip()

            if user_id and session_id:
                tracing_hook = TracingHook(
                    trace_id=self._trace_id,
                    user_id=user_id,
                    session_id=session_id,
                    channel=channel,
                )
                TracingHookRegistry.register(self._trace_id, tracing_hook)
                logger.debug("Registered tracing hook for trace: %s", self._trace_id)
            else:
                logger.warning("Skipping tracing hook registration: user_id=%s, session_id=%s",
                              user_id, session_id)
        except ImportError:
            logger.warning("Tracing hooks not available - tracing module not installed")
        except Exception as e:
            logger.warning("Failed to register tracing hook: %s", e)

    def set_trace_context(
        self,
        trace_id: str,
        user_id: str,
        session_id: str,
        channel: str,
    ) -> None:
        """Set tracing context for the agent.

        Args:
            trace_id: Trace identifier
            user_id: User identifier
            session_id: Session identifier
            channel: Channel identifier
        """
        self._trace_id = trace_id
        self._enable_tracing = True

        try:
            from .hooks import TracingHook, TracingHookRegistry

            tracing_hook = TracingHook(
                trace_id=trace_id,
                user_id=user_id,
                session_id=session_id,
                channel=channel,
            )
            TracingHookRegistry.register(trace_id, tracing_hook)
            logger.debug("Set tracing context: trace_id=%s", trace_id)
        except ImportError:
            logger.warning("Tracing module not available")
        except Exception as e:
            logger.warning("Failed to set tracing context: %s", e)

    def rebuild_sys_prompt(self) -> None:
        """Rebuild and replace the system prompt.

        Useful after load_session_state to ensure the prompt reflects
        the latest AGENTS.md / SOUL.md / PROFILE.md on disk.

        Updates both self._sys_prompt and the first system-role
        message stored in self.memory.content (if one exists).
        """
        self._sys_prompt = self._build_sys_prompt()

        for msg, _marks in self.memory.content:
            if msg.role == "system":
                msg.content = self.sys_prompt
            break

    async def register_mcp_clients(
        self,
        namesake_strategy: NamesakeStrategy = "skip",
    ) -> None:
        """Register MCP clients on this agent's toolkit after construction.

        Args:
            namesake_strategy: Strategy to handle namesake tool functions.
                Options: "override", "skip", "raise", "rename"
                (default: "skip")
        """
        for i, client in enumerate(self._mcp_clients):
            client_name = getattr(client, "name", repr(client))
            try:
                # Record tool-to-server mapping before registration
                tools = await client.list_tools()
                for tool in tools:
                    self._mcp_tool_to_server[tool.name] = client_name

                await self.toolkit.register_mcp_client(
                    client,
                    namesake_strategy=namesake_strategy,
                )
            except (ClosedResourceError, asyncio.CancelledError) as error:
                if self._should_propagate_cancelled_error(error):
                    raise
                logger.warning(
                    "MCP client '%s' session interrupted while listing tools; "
                    "trying recovery",
                    client_name,
                )
                recovered_client = await self._recover_mcp_client(client)
                if recovered_client is not None:
                    self._mcp_clients[i] = recovered_client
                    try:
                        # Record tool-to-server mapping before registration
                        tools = await recovered_client.list_tools()
                        for tool in tools:
                            self._mcp_tool_to_server[tool.name] = client_name

                        await self.toolkit.register_mcp_client(
                            recovered_client,
                            namesake_strategy=namesake_strategy,
                        )
                        continue
                    except asyncio.CancelledError as recover_error:
                        if self._should_propagate_cancelled_error(
                            recover_error,
                        ):
                            raise
                        logger.warning(
                            "MCP client '%s' registration cancelled after "
                            "recovery, skipping",
                            client_name,
                        )
                    except Exception as e:  # pylint: disable=broad-except
                        logger.warning(
                            "MCP client '%s' still unavailable after "
                            "recovery, skipping: %s",
                            client_name,
                            e,
                        )
                else:
                    logger.warning(
                        "MCP client '%s' recovery failed, skipping",
                        client_name,
                    )
            except Exception as e:  # pylint: disable=broad-except
                logger.exception(
                    "Unexpected error registering MCP client '%s': %s",
                    client_name,
                    e,
                )
                raise

    async def _recover_mcp_client(self, client: Any) -> Any | None:
        """Recover MCP client from broken session and return healthy client."""
        if await self._reconnect_mcp_client(client):
            return client

        rebuilt_client = self._rebuild_mcp_client(client)
        if rebuilt_client is None:
            return None

        if await self._reconnect_mcp_client(rebuilt_client):
            return self._reuse_shared_client_reference(
                original_client=client,
                rebuilt_client=rebuilt_client,
            )

        return None

    @staticmethod
    def _reuse_shared_client_reference(
        original_client: Any,
        rebuilt_client: Any,
    ) -> Any:
        """Keep manager-shared client reference stable after rebuild."""
        original_dict = getattr(original_client, "__dict__", None)
        rebuilt_dict = getattr(rebuilt_client, "__dict__", None)
        if isinstance(original_dict, dict) and isinstance(rebuilt_dict, dict):
            original_dict.update(rebuilt_dict)
            return original_client
        return rebuilt_client

    @staticmethod
    def _should_propagate_cancelled_error(error: BaseException) -> bool:
        """Only swallow MCP-internal cancellations, not task cancellation."""
        if not isinstance(error, asyncio.CancelledError):
            return False

        task = asyncio.current_task()
        if task is None:
            return False

        cancelling = getattr(task, "cancelling", None)
        if callable(cancelling):
            return cancelling() > 0

        # Python < 3.11: Task.cancelling() is unavailable.
        # Fall back to propagating CancelledError to avoid swallowing
        # genuine task cancellations when we cannot inspect the state.
        return True

    @staticmethod
    async def _reconnect_mcp_client(
        client: Any,
        timeout: float = 60.0,
    ) -> bool:
        """Best-effort reconnect for stateful MCP clients."""
        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            try:
                await close_fn()
            except asyncio.CancelledError:  # pylint: disable=try-except-raise
                raise
            except Exception:  # pylint: disable=broad-except
                pass

        connect_fn = getattr(client, "connect", None)
        if not callable(connect_fn):
            return False

        try:
            await asyncio.wait_for(connect_fn(), timeout=timeout)
            return True
        except asyncio.CancelledError:  # pylint: disable=try-except-raise
            raise
        except asyncio.TimeoutError:
            return False
        except Exception:  # pylint: disable=broad-except
            return False

    @staticmethod
    def _rebuild_mcp_client(client: Any) -> Any | None:
        """Rebuild a fresh MCP client instance from stored config metadata."""
        rebuild_info = getattr(client, "_copaw_rebuild_info", None)
        if not isinstance(rebuild_info, dict):
            return None

        transport = rebuild_info.get("transport")
        name = rebuild_info.get("name")

        try:
            if transport == "stdio":
                rebuilt_client = StdIOStatefulClient(
                    name=name,
                    command=rebuild_info.get("command"),
                    args=rebuild_info.get("args", []),
                    env=rebuild_info.get("env", {}),
                    cwd=rebuild_info.get("cwd"),
                )
                setattr(rebuilt_client, "_copaw_rebuild_info", rebuild_info)
                return rebuilt_client

            rebuilt_client = HttpStatefulClient(
                name=name,
                transport=transport,
                url=rebuild_info.get("url"),
                headers=rebuild_info.get("headers"),
            )
            setattr(rebuilt_client, "_copaw_rebuild_info", rebuild_info)
            return rebuilt_client
        except Exception:  # pylint: disable=broad-except
            return None

    def _get_model_name(self) -> str:
        """Get model name from model config.

        Returns:
            Model name string
        """
        if not hasattr(self, 'model') or not self.model:
            return "unknown"

        # Try model_name attribute (used by agentscope models)
        model_name = getattr(self.model, 'model_name', None)
        if model_name:
            return model_name

        # Try _model attribute (wrapped model)
        inner_model = getattr(self.model, '_model', None)
        if inner_model:
            model_name = getattr(inner_model, 'model_name', None)
            if model_name:
                return model_name

        # Fallback to model_id
        return getattr(self.model, 'model_id', 'unknown') or "unknown"

    def _extract_token_usage(
        self,
        result: Msg,
    ) -> tuple[int, int]:
        """Extract token usage from LLM response.

        Args:
            result: LLM response message

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        usage = self._get_usage_from_result(result)
        return self._parse_usage_tokens(usage)

    def _get_usage_from_result(self, result: Msg) -> Any:
        """Get usage object from result.

        Args:
            result: LLM response message

        Returns:
            Usage object or None
        """
        # 1. Check metadata.usage
        if result.metadata:
            usage = result.metadata.get('usage', {})
            if usage:
                return usage

        # 2. Check result.usage directly
        if hasattr(result, 'usage') and result.usage:
            return result.usage

        # 3. Try model's _last_usage
        if not hasattr(self, 'model') or not self.model:
            return None

        model = self.model
        if hasattr(model, '_last_usage') and model._last_usage:
            return model._last_usage

        return None

    def _parse_usage_tokens(self, usage: Any) -> tuple[int, int]:
        """Parse token counts from usage object.

        Args:
            usage: Usage object

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        if not usage:
            return 0, 0

        # ChatUsage object
        if hasattr(usage, 'input_tokens'):
            return usage.input_tokens or 0, usage.output_tokens or 0

        # Dict format
        if isinstance(usage, dict):
            output_tokens = (
                usage.get('completion_tokens', 0) or
                usage.get('output_tokens', 0) or
                usage.get('total_tokens', 0)
            )
            input_tokens = (
                usage.get('prompt_tokens', 0) or
                usage.get('input_tokens', 0)
            )
            return input_tokens, output_tokens

        return 0, 0

    async def _reasoning(
        self,
        tool_choice: Literal["auto", "none", "required"] | None = None,
    ) -> Msg:
        """Ensure a stable default tool-choice behavior across providers.

        Also emits tracing events for LLM calls if tracing is enabled.
        """
        tool_choice = normalize_reasoning_tool_choice(
            tool_choice=tool_choice,
            has_tools=bool(self.toolkit.get_json_schemas()),
        )

        # Emit LLM start event if tracing is enabled
        llm_span_id = None
        if self._enable_tracing and self._trace_id:
            llm_span_id = await self._emit_llm_start()

        # Call parent reasoning
        result = await super()._reasoning(tool_choice=tool_choice)

        # Emit LLM end event if tracing is enabled
        if llm_span_id:
            await self._emit_llm_end(result)

        return result

    async def _emit_llm_start(self) -> str | None:
        """Emit LLM start tracing event.

        Returns:
            Span ID or None
        """
        try:
            from .hooks import TracingHookRegistry

            hook = TracingHookRegistry.get(self._trace_id)
            if not hook:
                return None

            model_name = self._get_model_name()
            return await hook.on_llm_start(
                model_name=model_name,
                input_tokens=0,
            )
        except Exception as e:
            logger.debug("Failed to emit LLM start event: %s", e)
        return None

    async def _emit_llm_end(self, result: Msg) -> None:
        """Emit LLM end tracing event.

        Args:
            result: LLM response message
        """
        try:
            from .hooks import TracingHookRegistry

            hook = TracingHookRegistry.get(self._trace_id)
            if not hook:
                return

            input_tokens, output_tokens = self._extract_token_usage(result)
            logger.debug("Token usage: input=%d, output=%d",
                       input_tokens, output_tokens)
            await hook.on_llm_end(
                output_tokens=output_tokens,
                input_tokens=input_tokens,
            )
        except Exception as e:
            logger.debug("Failed to emit LLM end event: %s", e)

    def _detect_skill_call(
        self,
        tool_name: str,
        tool_input: dict,
    ) -> tuple[bool, str | None]:
        """Detect if a tool call is actually a skill invocation.

        Args:
            tool_name: Tool name
            tool_input: Tool input arguments

        Returns:
            Tuple of (is_skill, skill_name)
        """
        registered_skills = getattr(self, '_registered_skills', set())

        # 1. Direct skill call
        if tool_name in registered_skills:
            return True, tool_name

        # 2. Shell command executing a skill
        if tool_name != "execute_shell_command":
            return False, None

        command = tool_input.get("command", "")
        if not command:
            return False, None

        import re
        match = re.match(r'^copaw\s+(\w+)', command)
        if not match:
            return False, None

        potential_skill = match.group(1)
        if potential_skill in registered_skills:
            return True, potential_skill

        return False, None

    async def _emit_tool_start(
        self,
        tool_name: str,
        tool_input: dict,
        tool_call_id: str | None,
        is_skill: bool,
        skill_name: str | None,
    ) -> str | None:
        """Emit tool/skill start tracing event.

        Args:
            tool_name: Tool name
            tool_input: Tool input arguments
            tool_call_id: Tool call ID
            is_skill: Whether this is a skill invocation
            skill_name: Skill name if is_skill

        Returns:
            Span ID or None
        """
        try:
            from .hooks import TracingHookRegistry

            hook = TracingHookRegistry.get(self._trace_id)
            if not hook:
                return None

            if is_skill and skill_name:
                return await hook.on_skill_start(
                    skill_name=skill_name,
                    skill_input=tool_input,
                )

            mcp_server = self._mcp_tool_to_server.get(tool_name)
            return await hook.on_tool_start(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_call_id=tool_call_id,
                mcp_server=mcp_server,
            )
        except Exception as e:
            logger.debug("Failed to emit tool/skill start event: %s", e)
        return None

    async def _emit_tool_end(
        self,
        span_id: str | None,
        result: dict | None,
        error: str | None,
        tool_call_id: str | None,
        is_skill: bool,
    ) -> None:
        """Emit tool/skill end tracing event.

        Args:
            span_id: Span ID from start event
            result: Tool execution result
            error: Error message if failed
            tool_call_id: Tool call ID
            is_skill: Whether this is a skill invocation
        """
        if span_id is None:
            return

        try:
            from .hooks import TracingHookRegistry

            hook = TracingHookRegistry.get(self._trace_id)
            if not hook:
                return

            output, err_msg = self._prepare_tool_output(result, error)

            if is_skill:
                await hook.on_skill_end(skill_output=output, error=err_msg)
            else:
                await hook.on_tool_end(
                    tool_output=output,
                    tool_call_id=tool_call_id,
                    error=err_msg,
                )
        except Exception as e:
            logger.debug("Failed to emit tool/skill end event: %s", e)

    def _prepare_tool_output(
        self,
        result: dict | None,
        error: str | None,
    ) -> tuple[str, str | None]:
        """Prepare tool output for tracing.

        Args:
            result: Tool execution result
            error: Error message if failed

        Returns:
            Tuple of (output, error_message)
        """
        if error:
            return error[:500], error[:200]
        return self._truncate_result(result), None

    def _truncate_result(self, result: dict | None) -> str:
        """Truncate tool result for storage.

        Args:
            result: Tool execution result

        Returns:
            Truncated string representation
        """
        if result is None:
            return ""
        try:
            import json
            return json.dumps(result, ensure_ascii=False, default=str)[:500]
        except Exception:
            return str(result)[:500]

    async def _acting(self, tool_call: dict) -> dict | None:
        """Override tool execution to add tracing.

        Args:
            tool_call: Tool call dictionary with 'name' and 'input' keys

        Returns:
            Tool execution result
        """
        if not self._enable_tracing or not self._trace_id:
            return await super()._acting(tool_call)

        tool_name: str = tool_call.get("name", "")
        tool_input: dict = tool_call.get("input", {}) or {}
        tool_call_id = tool_call.get("id")

        # Detect if this is a skill call
        is_skill, skill_name = self._detect_skill_call(tool_name, tool_input)

        # Emit start event
        span_id = await self._emit_tool_start(
            tool_name, tool_input, tool_call_id, is_skill, skill_name
        )

        # Execute tool
        result = None
        error = None
        try:
            result = await super()._acting(tool_call)
            return result
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            await self._emit_tool_end(
                span_id, result, error, tool_call_id, is_skill
            )

    async def reply(
        self,
        msg: Msg | list[Msg] | None = None,
        structured_model: Type[BaseModel] | None = None,
    ) -> Msg:
        """Override reply to process file blocks and handle commands.

        Args:
            msg: Input message(s) from user
            structured_model: Optional pydantic model for structured output

        Returns:
            Response message
        """
        # Process file and media blocks in messages
        if msg is not None:
            await process_file_and_media_blocks_in_message(msg)

        # Check if message is a system command
        last_msg = msg[-1] if isinstance(msg, list) else msg
        query = (
            last_msg.get_text_content() if isinstance(last_msg, Msg) else None
        )

        if self.command_handler.is_command(query):
            logger.info(f"Received command: {query}")
            msg = await self.command_handler.handle_command(query)
            await self.print(msg)
            return msg

        # Normal message processing
        return await super().reply(msg=msg, structured_model=structured_model)

    async def interrupt(self, msg: Msg | list[Msg] | None = None) -> None:
        """Interrupt the current reply process and wait for cleanup."""
        if self._reply_task and not self._reply_task.done():
            task = self._reply_task
            task.cancel(msg)
            try:
                await task
            except asyncio.CancelledError:
                if not task.cancelled():
                    raise
            except Exception:
                logger.warning(
                    "Exception occurred during interrupt cleanup",
                    exc_info=True,
                )
