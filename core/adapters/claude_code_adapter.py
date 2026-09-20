#!/usr/bin/env python3
"""
Claude Code IDE Adapter for Neo Conflict Notifications

Integrates Neo's conflict detection with Claude Code's UI to show
real-time warnings when other agents are working on the same code.

Features:
- Shows conflict warning popups
- Displays conflicting agent info
- Suggests wait/override/coordinate actions
- Integrates with Claude Code's MCP protocol
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("Neo-Claude-Code-Adapter")


class ClaudeCodeAdapter:
    """Adapter for Claude Code IDE"""

    @staticmethod
    async def handle_conflict_notification(notification: Dict[str, Any]) -> bool:
        """
        Handle conflict notification in Claude Code

        Shows a popup-style warning in Claude Code with:
        - Risk level (LOW/MEDIUM/HIGH)
        - Conflicting agent info
        - File and region affected
        - Suggested action (proceed/wait/coordinate)
        """
        try:
            agent_id = notification.get("agent_id")
            conflicting_agent = notification.get("conflicting_agent")
            file_path = notification.get("file_path")
            risk_level = notification.get("risk_level")
            message = notification.get("message")
            region = notification.get("region")
            blocking = notification.get("blocking", False)

            # Build Claude Code notification message
            warning_message = build_claude_code_warning(
                agent_id=agent_id,
                conflicting_agent=conflicting_agent,
                file_path=file_path,
                region=region,
                risk_level=risk_level,
                message=message,
                blocking=blocking,
            )

            # Send via Claude Code's standard warning system
            await send_claude_code_warning(warning_message, risk_level, blocking)

            logger.info(f"Claude Code notified about conflict with {conflicting_agent}")
            return True

        except Exception as e:
            logger.error(f"Claude Code adapter error: {e}")
            return False


def build_claude_code_warning(
    agent_id: str,
    conflicting_agent: str,
    file_path: str,
    region: Optional[str],
    risk_level: str,
    message: str,
    blocking: bool,
) -> str:
    """Build Claude Code-formatted warning message"""

    severity_emoji = {
        "LOW": "🟢",
        "MEDIUM": "🟡",
        "HIGH": "🔴",
    }.get(risk_level, "⚪")

    action_text = "BLOCKING" if blocking else "CAUTION"

    warning = f"""
╔════════════════════════════════════════════════════════════════╗
║  {severity_emoji} Neo Coordination: {action_text} - {risk_level} Risk                     ║
╚════════════════════════════════════════════════════════════════╝

⚠️  Another Agent is Working Here

Agent:        {conflicting_agent}
File:         {file_path}
Region:       {region or 'entire file'}
Intent:       {message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actions:
  [Continue]        Proceed with your changes (may cause merge conflict)
  [Wait]            Wait for {conflicting_agent} to finish
  [Coordinate]      Send coordination request to other agent
  [Override]        Force proceed (expert mode)

{"🔴 BLOCKING: Cannot proceed - human coordination required" if blocking else "🟡 WARNING: Can proceed but coordination recommended"}
"""

    return warning


async def send_claude_code_warning(
    message: str,
    risk_level: str,
    blocking: bool,
) -> bool:
    """
    Send warning to Claude Code via MCP protocol

    Claude Code will show this as:
    - A persistent warning banner if MEDIUM risk
    - A blocking dialog if HIGH risk
    - An info message if LOW risk
    """
    try:
        # Message structure for Claude Code's MCP protocol
        mcp_message = {
            "type": "neo_conflict_warning",
            "severity": risk_level.lower(),
            "blocking": blocking,
            "content": message,
            "actions": [
                {"label": "Continue", "id": "continue"},
                {"label": "Wait", "id": "wait"},
                {"label": "Coordinate", "id": "coordinate"},
                {"label": "Override", "id": "override"},
            ] if not blocking else [
                {"label": "Coordinate", "id": "coordinate"},
                {"label": "Override", "id": "override"},
            ]
        }

        # Send via stdio to Claude Code (MCP standard)
        print(json.dumps(mcp_message))

        logger.debug(f"Sent warning to Claude Code: {risk_level}")
        return True

    except Exception as e:
        logger.error(f"Failed to send Claude Code warning: {e}")
        return False


async def handle_user_action(action_id: str, notification_id: str) -> Dict[str, Any]:
    """
    Handle user's response to conflict warning in Claude Code

    Called when user clicks: Continue, Wait, Coordinate, or Override
    """

    action_handlers = {
        "continue": handle_continue,
        "wait": handle_wait,
        "coordinate": handle_coordinate,
        "override": handle_override,
    }

    handler = action_handlers.get(action_id)
    if handler:
        return await handler(notification_id)

    return {"success": False, "error": f"Unknown action: {action_id}"}


async def handle_continue(notification_id: str) -> Dict[str, Any]:
    """User chose to continue despite conflict warning"""
    logger.info(f"User chose to continue on {notification_id}")
    return {
        "success": True,
        "action": "continue",
        "message": "Proceeding with your changes. Merge conflicts may occur."
    }


async def handle_wait(notification_id: str) -> Dict[str, Any]:
    """User chose to wait for other agent to finish"""
    logger.info(f"User chose to wait on {notification_id}")
    return {
        "success": True,
        "action": "wait",
        "message": "Waiting for other agent to complete. Check back soon.",
        "polling_interval_seconds": 5
    }


async def handle_coordinate(notification_id: str) -> Dict[str, Any]:
    """User chose to coordinate with other agent"""
    logger.info(f"User chose to coordinate on {notification_id}")
    return {
        "success": True,
        "action": "coordinate",
        "message": "Sending coordination request to other agent...",
        "next_step": "await_confirmation"
    }


async def handle_override(notification_id: str) -> Dict[str, Any]:
    """User chose to override conflict (expert mode)"""
    logger.warning(f"User overriding conflict on {notification_id}")
    return {
        "success": True,
        "action": "override",
        "message": "Override enabled. You take priority. Prepare for manual merge resolution.",
        "risk_level": "HIGH"
    }


# Export main handler
handle_conflict_notification = ClaudeCodeAdapter.handle_conflict_notification
