#!/usr/bin/env python3
"""Agent adapters for cross-agent orchestration.

Different AI agents (Claude, Devin, OpenAI) connect to Neo via different
interfaces (MCP, REST, Webhook). Adapters normalize these interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentInfo:
    """Information about an agent."""

    agent_id: str
    agent_type: str  # "claude", "devin", "openai", "custom"
    capabilities: List[str]  # ["architecture", "testing", "debugging"]
    max_concurrent_files: int = 3
    registered_at: Optional[float] = None
    last_activity: Optional[float] = None
    status: str = "idle"  # "idle", "working", "waiting", "error"


class AgentAdapter(ABC):
    """Abstract base class for agent adapters."""

    @abstractmethod
    def check_conflicts(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check for conflicts before code generation.

        Args:
            agent_id: Unique agent identifier
            file_path: File being modified
            intent: Description of intended work
            region: Optional code region

        Returns:
            {
                "risk_level": "LOW" | "MEDIUM" | "HIGH",
                "message": str,
                "should_block": bool,
                "lock_holder": str or None,
                "queue_position": int or None
            }
        """
        pass

    @abstractmethod
    def declare_intent(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Declare intent to work on a file.

        Args:
            agent_id: Unique agent identifier
            file_path: File being modified
            intent: Description of work
            region: Optional code region
            dependencies: List of dependent files (file:region format)

        Returns:
            {"success": bool, "lock_state": str, "message": str}
        """
        pass

    @abstractmethod
    def log_completion(
        self,
        agent_id: str,
        file_path: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Log work completion.

        Args:
            agent_id: Agent identifier
            file_path: File modified
            metadata: Completion metadata (lines_added, lines_removed, etc.)

        Returns:
            {"success": bool, "message": str}
        """
        pass

    @abstractmethod
    def register_agent(
        self,
        agent_info: AgentInfo,
    ) -> Dict[str, Any]:
        """Register agent with Neo.

        Args:
            agent_info: Agent information

        Returns:
            {"success": bool, "agent_id": str, "message": str}
        """
        pass

    @abstractmethod
    def get_fresh_context(
        self,
        agent_id: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """Get fresh context after lock is released.

        Args:
            agent_id: Requesting agent
            file_path: File to get context for

        Returns:
            {
                "previous_agent": str,
                "changes": {...},
                "summary": str,
                "next_steps": [...]
            }
        """
        pass


class MCPAdapter(AgentAdapter):
    """MCP (Model Context Protocol) adapter for Claude Code.

    Claude Code calls Neo via MCP tools.
    """

    def __init__(self):
        self.agent_registry: Dict[str, AgentInfo] = {}

    def check_conflicts(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check conflicts via MCP neo_check_conflicts tool."""
        from core.pre_gen_check import check_for_conflicts

        risk_level, message, lock_info = check_for_conflicts(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
        )

        return {
            "risk_level": risk_level.value if hasattr(risk_level, "value") else str(risk_level),
            "message": message,
            "should_block": str(risk_level).upper() == "HIGH",
            "lock_holder": lock_info.get("lock_holder") if lock_info else None,
            "queue_position": lock_info.get("queue_position") if lock_info else None,
        }

    def declare_intent(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Declare intent via MCP neo_log_activity tool."""
        from core.activity_log import log_activity

        try:
            entry = log_activity(
                developer_id=agent_id,
                file_path=file_path,
                intent=intent,
                region=region,
                intent_category="feature" if not region else "refactor",
                agent_metadata={"dependencies": dependencies or []},
            )
            return {
                "success": True,
                "lock_state": entry.lock_state,
                "message": f"Intent declared for {agent_id} on {file_path}",
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to declare intent: {str(e)}"}

    def log_completion(
        self,
        agent_id: str,
        file_path: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Log completion via MCP neo_log_activity tool."""
        from core.activity_log import log_activity

        try:
            entry = log_activity(
                developer_id=agent_id,
                file_path=file_path,
                intent=f"COMPLETED: {metadata.get('summary', 'Work completed')}",
                agent_metadata=metadata,
            )
            return {"success": True, "message": "Work completion logged"}
        except Exception as e:
            return {"success": False, "message": f"Failed to log completion: {str(e)}"}

    def register_agent(self, agent_info: AgentInfo) -> Dict[str, Any]:
        """Register agent in local registry."""
        import time

        agent_info.registered_at = time.time()
        agent_info.status = "idle"
        self.agent_registry[agent_info.agent_id] = agent_info
        return {
            "success": True,
            "agent_id": agent_info.agent_id,
            "message": f"Agent {agent_info.agent_id} registered as {agent_info.agent_type}",
        }

    def get_fresh_context(
        self,
        agent_id: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """Get fresh context after lock release."""
        from core.activity_log import read_log

        entries = read_log()
        # Find most recent completed entry for this file
        for entry in reversed(entries):
            if entry.get("file_path") == file_path and entry.get(
                "agent_metadata", {}
            ).get("status") == "completed":
                return {
                    "previous_agent": entry["developer_id"],
                    "changes": entry.get("agent_metadata", {}),
                    "summary": entry.get("intent", "").replace("COMPLETED: ", ""),
                    "next_steps": entry.get("agent_metadata", {}).get("next_steps", []),
                }
        return {
            "previous_agent": None,
            "changes": {},
            "summary": "No previous work",
            "next_steps": [],
        }


class RESTAdapter(AgentAdapter):
    """REST API adapter for external agents (Devin, OpenAI, custom).

    External agents call Neo via HTTP REST API.
    """

    def __init__(self, base_url: str = "http://neo-server:8000"):
        self.base_url = base_url
        self.agent_registry: Dict[str, AgentInfo] = {}

    def check_conflicts(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check conflicts via REST API."""
        # In production, would POST to {base_url}/api/conflicts/check
        # For now, delegate to MCP adapter
        mcp = MCPAdapter()
        return mcp.check_conflicts(agent_id, file_path, intent, region)

    def declare_intent(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Declare intent via REST API."""
        mcp = MCPAdapter()
        return mcp.declare_intent(agent_id, file_path, intent, region, dependencies)

    def log_completion(
        self,
        agent_id: str,
        file_path: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Log completion via REST API."""
        mcp = MCPAdapter()
        return mcp.log_completion(agent_id, file_path, metadata)

    def register_agent(self, agent_info: AgentInfo) -> Dict[str, Any]:
        """Register agent via REST API."""
        import time

        agent_info.registered_at = time.time()
        agent_info.status = "idle"
        self.agent_registry[agent_info.agent_id] = agent_info
        return {
            "success": True,
            "agent_id": agent_info.agent_id,
            "message": f"Agent {agent_info.agent_id} registered (REST)",
        }

    def get_fresh_context(
        self,
        agent_id: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """Get fresh context via REST API."""
        mcp = MCPAdapter()
        return mcp.get_fresh_context(agent_id, file_path)


def get_adapter(adapter_type: str = "mcp") -> AgentAdapter:
    """Get appropriate adapter for agent type.

    Args:
        adapter_type: "mcp" or "rest"

    Returns:
        Adapter instance
    """
    if adapter_type == "mcp":
        return MCPAdapter()
    elif adapter_type == "rest":
        return RESTAdapter()
    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}")
