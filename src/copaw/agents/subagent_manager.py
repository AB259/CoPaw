# -*- coding: utf-8 -*-
"""Sub-Agent Manager.

This module provides the SubAgentManager class for managing the lifecycle
of sub-agent instances.
"""
import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Literal, Optional

from agentscope.message import Msg, TextBlock
from agentscope.tool import ToolResponse
from pydantic import BaseModel, ConfigDict

from .subagent_config import SubAgentConfig

logger = logging.getLogger(__name__)


class SubAgentInstance(BaseModel):
    """Represents a running sub-agent instance.

    Attributes:
        agent_id: Unique identifier for this agent
        config: Configuration used to create this agent
        agent: The actual agent instance
        status: Current status of the agent
        created_at: Unix timestamp when agent was created
        started_at: Unix timestamp when execution started
        completed_at: Unix timestamp when execution completed
        result: ToolResponse with execution result (if completed)
        error: Error message if execution failed
        task: Asyncio task for background execution
    """

    agent_id: str
    config: SubAgentConfig
    agent: Optional[Any] = None  # CoPawAgent instance
    status: Literal["created", "running", "completed", "failed", "cancelled"] = (
        "created"
    )
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[ToolResponse] = None
    error: Optional[str] = None
    task: Optional["asyncio.Task[Any]"] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SubAgentManager:
    """Central manager for sub-agent lifecycle and execution.

    This is a singleton that tracks all active sub-agents and provides
    methods for creating, executing, and managing them.
    """

    _instance: Optional["SubAgentManager"] = None

    def __init__(self):
        """Initialize SubAgentManager."""
        self._agents: Dict[str, SubAgentInstance] = {}
        self._lock = asyncio.Lock()
        self._task_counter = 0
        self._max_concurrent = 5

    @classmethod
    def get_instance(cls) -> "SubAgentManager":
        """Get the singleton instance of SubAgentManager.

        Returns:
            The SubAgentManager instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def create_agent(
        self,
        config: SubAgentConfig,
        agent_instance: Any,  # CoPawAgent
    ) -> str:
        """Create a new sub-agent instance.

        Args:
            config: Configuration for the sub-agent
            agent_instance: The actual agent object

        Returns:
            The agent ID

        Raises:
            ValueError: If maximum concurrent agents reached
        """
        async with self._lock:
            # Check concurrent limit
            running_count = sum(
                1 for inst in self._agents.values() if inst.status == "running"
            )
            if running_count >= self._max_concurrent:
                raise ValueError(
                    f"Maximum concurrent sub-agents ({self._max_concurrent}) reached. "
                    "Please wait for some to complete."
                )

            # Generate unique agent ID
            agent_id = f"agent_{uuid.uuid4().hex[:12]}"

            # Create instance
            instance = SubAgentInstance(
                agent_id=agent_id,
                config=config,
                agent=agent_instance,
                created_at=time.time(),
            )

            self._agents[agent_id] = instance
            logger.info(f"Created sub-agent: {agent_id} (type: {config.agent_type})")

            return agent_id

    async def execute_agent(
        self,
        agent_id: str,
        prompt: str,
        run_in_background: bool = False,
    ) -> ToolResponse:
        """Execute a sub-agent task.

        Args:
            agent_id: The agent ID to execute
            prompt: The task prompt
            run_in_background: If True, return immediately with task ID

        Returns:
            ToolResponse with result or task information
        """
        if agent_id not in self._agents:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error: Agent ID '{agent_id}' not found.",
                    )
                ]
            )

        instance = self._agents[agent_id]

        if instance.status == "running":
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Agent '{agent_id}' is already running.",
                    )
                ]
            )

        if run_in_background:
            # Start background task
            instance.task = asyncio.create_task(
                self._execute_background(instance, prompt)
            )
            return ToolResponse(
                content=[
                    TextBlock(type="text", text="Sub-agent started in background."),
                    TextBlock(type="text", text=f"Task ID: {agent_id}"),
                    TextBlock(
                        type="text",
                        text="Use get_agent_status() to check progress.",
                    ),
                ]
            )
        else:
            # Execute synchronously
            return await self._execute_sync(instance, prompt)

    async def _execute_sync(
        self,
        instance: SubAgentInstance,
        prompt: str,
    ) -> ToolResponse:
        """Execute sub-agent synchronously."""
        instance.status = "running"
        instance.started_at = time.time()

        try:
            msg = Msg(name="user", role="user", content=prompt)

            # Execute with timeout
            timeout = instance.config.timeout
            result = await asyncio.wait_for(
                self._run_agent(instance.agent, msg),
                timeout=timeout,
            )

            instance.status = "completed"
            instance.completed_at = time.time()

            response_text = self._extract_response_text(result)
            instance.result = ToolResponse(
                content=[TextBlock(type="text", text=response_text)]
            )

            return instance.result

        except asyncio.TimeoutError:
            instance.status = "failed"
            instance.completed_at = time.time()
            instance.error = f"Timeout after {timeout} seconds"
            logger.error(f"Sub-agent {instance.agent_id} timed out")

            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Sub-agent timed out after {timeout} seconds.",
                    )
                ]
            )

        except Exception as e:
            instance.status = "failed"
            instance.completed_at = time.time()
            instance.error = str(e)
            logger.exception(f"Sub-agent {instance.agent_id} failed: {e}")

            return ToolResponse(
                content=[TextBlock(type="text", text=f"Sub-agent failed: {str(e)}")]
            )

    async def _execute_background(
        self,
        instance: SubAgentInstance,
        prompt: str,
    ) -> None:
        """Execute sub-agent in background."""
        await self._execute_sync(instance, prompt)

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed status of a sub-agent.

        Args:
            agent_id: The agent ID

        Returns:
            Status dictionary with agent information
        """
        if agent_id not in self._agents:
            return {
                "agent_id": agent_id,
                "status": "not_found",
                "error": "Agent ID not found",
            }

        instance = self._agents[agent_id]

        return {
            "agent_id": instance.agent_id,
            "type": instance.config.agent_type,
            "description": instance.config.description,
            "status": instance.status,
            "created_at": instance.created_at,
            "started_at": instance.started_at,
            "completed_at": instance.completed_at,
            "duration": (
                instance.completed_at - instance.started_at
                if instance.started_at and instance.completed_at
                else None
            ),
            "error": instance.error,
            "has_result": instance.result is not None,
        }

    async def list_agents(
        self,
        parent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all active sub-agents.

        Args:
            parent_id: If specified, only return sub-agents of this parent

        Returns:
            List of agent status dictionaries
        """
        agents_list = []

        for agent_id, instance in self._agents.items():
            if parent_id and instance.config.parent_id != parent_id:
                continue

            status_info = await self.get_agent_status(agent_id)
            agents_list.append(status_info)

        # Sort by created time (newest first)
        agents_list.sort(
            key=lambda x: x.get("created_at", 0), reverse=True
        )

        return agents_list

    async def cancel_agent(self, agent_id: str) -> bool:
        """Cancel a running sub-agent.

        Args:
            agent_id: The agent ID to cancel

        Returns:
            True if cancelled, False otherwise
        """
        if agent_id not in self._agents:
            return False

        instance = self._agents[agent_id]

        if instance.status != "running":
            return False

        if instance.task and not instance.task.done():
            instance.task.cancel()

            # Wait for cancellation
            try:
                await asyncio.wait_for(instance.task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        instance.status = "cancelled"
        instance.completed_at = time.time()
        logger.info(f"Cancelled sub-agent: {agent_id}")

        return True

    async def cleanup_completed(self) -> None:
        """Clean up completed agents after a delay.

        Removes:
        - Completed agents after 1 hour
        - Failed/cancelled agents after 5 minutes
        """
        COMPLETED_KEEP_DURATION = 3600  # 1 hour
        FAILED_KEEP_DURATION = 300  # 5 minutes

        now = time.time()
        to_remove = []

        for agent_id, instance in self._agents.items():
            if instance.status not in ["completed", "failed", "cancelled"]:
                continue

            if not instance.completed_at:
                continue

            duration = now - instance.completed_at
            keep_duration = (
                COMPLETED_KEEP_DURATION
                if instance.status == "completed"
                else FAILED_KEEP_DURATION
            )

            if duration > keep_duration:
                to_remove.append(agent_id)

        for agent_id in to_remove:
            del self._agents[agent_id]
            logger.debug(f"Cleaned up sub-agent: {agent_id}")

    def _extract_response_text(self, result: Any) -> str:
        """Extract text content from agent response.

        Args:
            result: The agent response object

        Returns:
            Extracted text string
        """
        try:
            # Try different response formats
            if hasattr(result, "text"):
                return result.text
            elif hasattr(result, "content"):
                return str(result.content)
            elif hasattr(result, "get_text_content"):
                return result.get_text_content()
            else:
                return str(result)
        except Exception:
            return str(result)

    @staticmethod
    async def _run_agent(agent: Any, msg: Msg) -> Any:
        """Run a sub-agent with the most compatible invocation style."""
        reply_fn = getattr(agent, "reply", None)
        if callable(reply_fn):
            return await reply_fn(msg=msg)
        return await agent(msg)
