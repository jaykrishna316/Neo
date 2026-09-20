#!/usr/bin/env python3
"""
Devin IDE Adapter for Neo Conflict Notifications

Integrates Neo's conflict detection with Devin's UI to show
real-time warnings about conflicting agent work.

Features:
- Devin-compatible warning format
- Task synchronization awareness
- Multi-agent coordination prompts
- Terminal/UI-friendly output
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger("Neo-Devin-Adapter")


class DevinAdapter:
    """Adapter for Devin IDE/Agent"""

    @staticmethod
    async def handle_conflict_notification(notification: Dict[str, Any]) -> bool:
        """
        Handle conflict notification in Devin

        Displays warning in Devin's task panel showing:
        - Status: Other agent working on same code
        - File and region affected
        - Recommended action
        - Waiting/coordination options
        """
        try:
            agent_id = notification.get("agent_id")
            conflicting_agent = notification.get("conflicting_agent")
            file_path = notification.get("file_path")
            risk_level = notification.get("risk_level")
            message = notification.get("message")
            region = notification.get("region")
            blocking = notification.get("blocking", False)

            # Build Devin-specific warning
            warning = build_devin_warning(
                agent_id=agent_id,
                conflicting_agent=conflicting_agent,
                file_path=file_path,
                region=region,
                risk_level=risk_level,
                message=message,
                blocking=blocking,
            )

            # Send to Devin via task status update
            await send_devin_task_update(warning, risk_level, blocking)

            logger.info(f"Devin notified about conflict with {conflicting_agent}")
            return True

        except Exception as e:
            logger.error(f"Devin adapter error: {e}")
            return False


def build_devin_warning(
    agent_id: str,
    conflicting_agent: str,
    file_path: str,
    region: Optional[str],
    risk_level: str,
    message: str,
    blocking: bool,
) -> str:
    """Build Devin-formatted warning message"""

    status_icon = {
        "LOW": "✓",
        "MEDIUM": "⚠️",
        "HIGH": "🛑",
    }.get(risk_level, "ℹ️")

    timestamp = datetime.now().strftime("%H:%M:%S")

    warning = f"""
[{timestamp}] {status_icon} NEO COORDINATION ALERT [{risk_level}]

╭─ Conflict Detected ─────────────────────────────────────────╮
│
│  Another agent is working on this code:
│
│  🤖 Agent:     {conflicting_agent}
│  📄 File:      {file_path}
│  📍 Region:    {region or '(entire file)'}
│  💭 Intent:    {message}
│
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│
│  Your Options:
│
│  1️⃣  [CONTINUE]    Proceed with your changes
│                  (May cause merge conflicts later)
│
│  2️⃣  [WAIT]        Pause and wait for {conflicting_agent} to finish
│                  (Recommended for {risk_level} risk)
│
│  3️⃣  [COORDINATE]  Send message to {conflicting_agent}
│                  (Request synchronized completion)
│
{"│" if not blocking else "│  ⚠️  BLOCKING: Coordination required before proceeding"}
│
╰──────────────────────────────────────────────────────────────╯

Type your choice (1/2/3) or 'help' for more options:
"""

    return warning


async def send_devin_task_update(
    message: str,
    risk_level: str,
    blocking: bool,
) -> bool:
    """
    Send task status update to Devin

    Updates Devin's task panel to show conflict awareness
    """
    try:
        # Devin's task status structure
        task_update = {
            "type": "neo_conflict_status",
            "status": "paused" if blocking else "warning",
            "risk_level": risk_level.lower(),
            "message": message,
            "blocking": blocking,
            "timestamp": datetime.now().isoformat(),
        }

        # Log to Devin's task output
        print(message)

        # Also log to Neo's Devin-specific log
        log_to_devin_log(task_update)

        logger.debug(f"Sent task update to Devin: {risk_level}")
        return True

    except Exception as e:
        logger.error(f"Failed to send Devin task update: {e}")
        return False


def log_to_devin_log(update: Dict[str, Any]):
    """Log status update to Devin-specific log file"""
    from pathlib import Path

    devin_log = Path(".devsync/devin_task_log.jsonl")
    devin_log.parent.mkdir(parents=True, exist_ok=True)

    with open(devin_log, "a") as f:
        f.write(json.dumps(update) + "\n")


async def handle_devin_response(choice: str, notification_id: str) -> Dict[str, Any]:
    """Handle Devin user's choice from conflict prompt"""

    handlers = {
        "1": handle_devin_continue,
        "continue": handle_devin_continue,
        "2": handle_devin_wait,
        "wait": handle_devin_wait,
        "3": handle_devin_coordinate,
        "coordinate": handle_devin_coordinate,
        "help": handle_devin_help,
    }

    handler = handlers.get(choice.lower())
    if handler:
        return await handler(notification_id)

    return {
        "success": False,
        "error": f"Unknown choice: {choice}",
        "valid_choices": ["1", "2", "3", "help"]
    }


async def handle_devin_continue(notification_id: str) -> Dict[str, Any]:
    """Devin chose to continue"""
    logger.info(f"Devin chose to continue on {notification_id}")
    return {
        "success": True,
        "choice": "continue",
        "message": "✓ Continuing with your changes. Watch for merge conflicts during git commit.",
    }


async def handle_devin_wait(notification_id: str) -> Dict[str, Any]:
    """Devin chose to wait"""
    logger.info(f"Devin chose to wait on {notification_id}")
    return {
        "success": True,
        "choice": "wait",
        "message": "⏸ Pausing execution. Checking other agent's progress...",
        "check_interval": 5,  # seconds
        "max_wait": 1800,     # 30 minutes
    }


async def handle_devin_coordinate(notification_id: str) -> Dict[str, Any]:
    """Devin chose to coordinate"""
    logger.info(f"Devin chose to coordinate on {notification_id}")
    return {
        "success": True,
        "choice": "coordinate",
        "message": "🤝 Sending coordination request to other agent...",
        "next_action": "await_ack",
        "timeout": 30,
    }


async def handle_devin_help(_: str) -> Dict[str, Any]:
    """Show help options"""
    return {
        "success": True,
        "type": "help",
        "content": """
Neo Coordination Options:

1. CONTINUE
   Proceed immediately with your changes.
   ✓ Fast, makes progress
   ✗ May cause merge conflicts
   Use when: You're confident changes don't overlap

2. WAIT
   Pause and wait for the other agent to finish.
   ✓ Avoids conflicts, clean merge
   ✗ Slower, blocks your progress
   Use when: Changes are tightly coupled

3. COORDINATE
   Propose synchronized completion with other agent.
   ✓ Optimized outcome, both agents aligned
   ✗ Requires communication, takes time
   Use when: Changes must be coordinated

Type your choice (1/2/3) to proceed.
"""
    }


# Export main handler
handle_conflict_notification = DevinAdapter.handle_conflict_notification
