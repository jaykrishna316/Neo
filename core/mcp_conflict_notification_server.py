#!/usr/bin/env python3
"""
MCP Conflict Notification Server for Neo Coordination Layer
Sends real-time conflict warnings to IDEs via MCP protocol

Supports:
- Claude Code (via MCP stdio)
- Devin (via custom MCP adapter)
- OpenAI/Cursor (via standard MCP)
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Neo-MCP-Server")


class ConflictSeverity(Enum):
    """Severity levels for conflict notifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ConflictNotification:
    """Real-time conflict notification sent to IDEs"""
    notification_id: str
    timestamp: str
    agent_id: str
    conflicting_agent: str
    file_path: str
    intent: str
    risk_level: str
    message: str
    region: Optional[str] = None
    blocking: bool = False
    suggested_action: str = "proceed"  # proceed, wait, coordinate

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class MCPConflictServer:
    """MCP server for broadcasting conflict notifications to IDEs"""

    def __init__(self, host: str = "localhost", port: int = 9000):
        self.host = host
        self.port = port
        self.clients: Dict[str, Any] = {}  # Connected IDE clients
        self.notification_handlers: Dict[str, List[Callable]] = {
            "claude-code": [],
            "devin": [],
            "openai": [],
        }
        self.conflict_log = Path(".devsync/conflict_notifications.log")
        self._setup_logging()

    def _setup_logging(self):
        """Setup notification logging"""
        self.conflict_log.parent.mkdir(parents=True, exist_ok=True)
        if not self.conflict_log.exists():
            self.conflict_log.write_text("[]")

    def register_handler(self, ide_type: str, handler: Callable):
        """Register a notification handler for an IDE"""
        if ide_type in self.notification_handlers:
            self.notification_handlers[ide_type].append(handler)
            logger.info(f"Handler registered for {ide_type}")

    async def notify_conflict(
        self,
        agent_id: str,
        conflicting_agent: str,
        file_path: str,
        intent: str,
        risk_level: str,
        message: str,
        region: Optional[str] = None,
        ide_targets: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        Broadcast conflict notification to specified IDEs

        Args:
            agent_id: Agent requesting the notification
            conflicting_agent: Agent that's blocking
            file_path: File with conflict
            intent: What the agent is trying to do
            risk_level: LOW/MEDIUM/HIGH
            message: Detailed message
            region: Code region affected
            ide_targets: Which IDEs to notify (default: all)

        Returns:
            Dict of {ide_name: success}
        """
        notification_id = f"conflict-{datetime.now().isoformat()}"
        blocking = risk_level == "HIGH"
        suggested_action = "wait" if blocking else "proceed"

        notification = ConflictNotification(
            notification_id=notification_id,
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            conflicting_agent=conflicting_agent,
            file_path=file_path,
            intent=intent,
            risk_level=risk_level,
            message=message,
            region=region,
            blocking=blocking,
            suggested_action=suggested_action,
        )

        # Log notification
        self._log_notification(notification)

        # Determine targets
        targets = ide_targets or list(self.notification_handlers.keys())

        results = {}
        for ide_type in targets:
            if ide_type in self.notification_handlers:
                success = await self._send_to_ide(ide_type, notification)
                results[ide_type] = success
            else:
                results[ide_type] = False

        logger.info(f"Conflict notification {notification_id} sent to {results}")
        return results

    async def _send_to_ide(self, ide_type: str, notification: ConflictNotification) -> bool:
        """Send notification to a specific IDE type"""
        try:
            handlers = self.notification_handlers.get(ide_type, [])
            notification_dict = notification.to_dict()
            for handler in handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(notification_dict)
                else:
                    handler(notification_dict)
            return True
        except Exception as e:
            logger.error(f"Failed to send to {ide_type}: {e}")
            return False

    def _log_notification(self, notification: ConflictNotification):
        """Log notification to persistent storage"""
        try:
            entries = json.loads(self.conflict_log.read_text())
            entries.append(notification.to_dict())
            self.conflict_log.write_text(json.dumps(entries, indent=2))
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")

    def get_notifications(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Retrieve logged notifications"""
        try:
            entries = json.loads(self.conflict_log.read_text())
            if agent_id:
                return [e for e in entries if e.get("agent_id") == agent_id]
            return entries
        except Exception as e:
            logger.error(f"Failed to retrieve notifications: {e}")
            return []


# Global MCP server instance
_mcp_server: Optional[MCPConflictServer] = None


def get_mcp_server() -> MCPConflictServer:
    """Get or create the global MCP server"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPConflictServer()
    return _mcp_server


async def notify_ide_of_conflict(
    agent_id: str,
    conflicting_agent: str,
    file_path: str,
    intent: str,
    risk_level: str,
    message: str,
    region: Optional[str] = None,
    ide_targets: Optional[List[str]] = None,
) -> Dict[str, bool]:
    """
    Convenience function to send conflict notification to IDEs

    Usage:
        from core.mcp_conflict_notification_server import notify_ide_of_conflict

        await notify_ide_of_conflict(
            agent_id="claude-code",
            conflicting_agent="devin-agent",
            file_path="src/auth.py",
            intent="Add OAuth2 support",
            risk_level="MEDIUM",
            message="Devin is working on authenticate() function",
            region="authenticate() lines 20-40",
            ide_targets=["claude-code"]  # Or None for all IDEs
        )
    """
    server = get_mcp_server()
    return await server.notify_conflict(
        agent_id=agent_id,
        conflicting_agent=conflicting_agent,
        file_path=file_path,
        intent=intent,
        risk_level=risk_level,
        message=message,
        region=region,
        ide_targets=ide_targets,
    )


def setup_mcp_handlers():
    """Setup IDE-specific notification handlers"""
    try:
        from core.adapters import claude_code_adapter, devin_adapter, openai_adapter
    except ImportError:
        from adapters import claude_code_adapter, devin_adapter, openai_adapter

    server = get_mcp_server()

    # Register handlers
    server.register_handler("claude-code", claude_code_adapter.handle_conflict_notification)
    server.register_handler("devin", devin_adapter.handle_conflict_notification)
    server.register_handler("openai", openai_adapter.handle_conflict_notification)

    logger.info("MCP handlers registered for all IDEs")


if __name__ == "__main__":
    # Test server
    import asyncio

    async def test():
        setup_mcp_handlers()
        server = get_mcp_server()

        print("Testing MCP Conflict Notification Server...")
        results = await notify_ide_of_conflict(
            agent_id="test-agent",
            conflicting_agent="other-agent",
            file_path="test.py",
            intent="Add feature",
            risk_level="MEDIUM",
            message="Test notification",
        )
        print(f"Results: {results}")
        print(f"Logged notifications: {server.get_notifications()}")

    asyncio.run(test())
