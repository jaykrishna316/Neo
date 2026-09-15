#!/usr/bin/env python3
"""
OpenAI/Cursor IDE Adapter for Neo Conflict Notifications

Integrates Neo's conflict detection with OpenAI Cursor and other
OpenAI-based code editors.

Features:
- Cursor's native notification system
- OpenAI API compatible warnings
- Inline code comments for conflicts
- Chat-based coordination prompts
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger("Neo-OpenAI-Adapter")


class OpenAIAdapter:
    """Adapter for OpenAI/Cursor IDE"""

    @staticmethod
    async def handle_conflict_notification(notification: Dict[str, Any]) -> bool:
        """
        Handle conflict notification in OpenAI/Cursor

        Shows warning via:
        - Inline comments in affected code regions
        - Chat sidebar message
        - Status bar indicator
        """
        try:
            agent_id = notification.get("agent_id")
            conflicting_agent = notification.get("conflicting_agent")
            file_path = notification.get("file_path")
            risk_level = notification.get("risk_level")
            message = notification.get("message")
            region = notification.get("region")
            blocking = notification.get("blocking", False)

            # Send to Cursor via multiple channels
            await send_cursor_notification(
                agent_id=agent_id,
                conflicting_agent=conflicting_agent,
                file_path=file_path,
                region=region,
                risk_level=risk_level,
                message=message,
                blocking=blocking,
            )

            logger.info(f"Cursor notified about conflict with {conflicting_agent}")
            return True

        except Exception as e:
            logger.error(f"OpenAI adapter error: {e}")
            return False


async def send_cursor_notification(
    agent_id: str,
    conflicting_agent: str,
    file_path: str,
    region: Optional[str],
    risk_level: str,
    message: str,
    blocking: bool,
) -> bool:
    """Send conflict notification to Cursor via multiple channels"""

    try:
        # 1. Chat message (primary)
        chat_message = build_cursor_chat_message(
            agent_id, conflicting_agent, file_path, region, risk_level, message, blocking
        )
        await send_cursor_chat(chat_message)

        # 2. Inline code comment
        code_comment = build_cursor_code_comment(
            conflicting_agent, risk_level, message
        )
        await add_cursor_inline_comment(file_path, region, code_comment)

        # 3. Status bar notification
        status_message = f"🔴 {conflicting_agent} working on {file_path}" if blocking else f"🟡 Conflict detected in {file_path}"
        await set_cursor_status(status_message, risk_level)

        return True

    except Exception as e:
        logger.error(f"Failed to send Cursor notification: {e}")
        return False


def build_cursor_chat_message(
    agent_id: str,
    conflicting_agent: str,
    file_path: str,
    region: Optional[str],
    risk_level: str,
    message: str,
    blocking: bool,
) -> str:
    """Build Cursor chat message for conflict notification"""

    emoji = {
        "LOW": "✅",
        "MEDIUM": "⚠️",
        "HIGH": "🛑",
    }.get(risk_level, "ℹ️")

    chat_msg = f"""{emoji} **Neo Coordination Alert** [{risk_level}]

Another agent is working on the code you're about to modify:

- **Agent:** {conflicting_agent}
- **File:** `{file_path}`
- **Region:** {region or '(entire file)'}
- **Intent:** {message}

{"🔴 **BLOCKING:** Coordination is required. You cannot proceed until the conflict is resolved." if blocking else "⚠️ **WARNING:** You can proceed, but merge conflicts may occur."}

**Recommended Actions:**

1. **Wait** - Pause and let {conflicting_agent} finish first
2. **Coordinate** - Send a coordination message to sync work
3. **Continue** - Proceed with your changes anyway
4. **Override** - Force priority (expert mode)

What would you like to do?
"""

    return chat_msg


def build_cursor_code_comment(
    conflicting_agent: str,
    risk_level: str,
    message: str,
) -> str:
    """Build inline code comment for conflict region"""

    severity_marker = {
        "LOW": "// ✓",
        "MEDIUM": "// ⚠️",
        "HIGH": "// 🛑",
    }.get(risk_level, "// ℹ️")

    comment = f"""{severity_marker} [Neo] {conflicting_agent} is modifying this region
{severity_marker} Conflict Level: {risk_level}
{severity_marker} Intent: {message}
{severity_marker} Consider waiting or coordinating to avoid merge conflicts"""

    return comment


async def send_cursor_chat(message: str) -> bool:
    """Send message to Cursor's chat sidebar"""
    try:
        # Cursor chat message format
        chat_payload = {
            "type": "neo_coordination",
            "channel": "chat",
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "priority": "high",
        }

        # Output for Cursor to capture
        print(json.dumps(chat_payload))

        logger.debug("Sent message to Cursor chat")
        return True

    except Exception as e:
        logger.error(f"Failed to send Cursor chat: {e}")
        return False


async def add_cursor_inline_comment(
    file_path: str,
    region: Optional[str],
    comment: str,
) -> bool:
    """Add inline comment to code region in Cursor"""
    try:
        inline_comment = {
            "type": "neo_inline_comment",
            "file": file_path,
            "region": region,
            "comment": comment,
            "editable": False,  # Read-only comment
            "timestamp": datetime.now().isoformat(),
        }

        print(json.dumps(inline_comment))

        logger.debug(f"Added inline comment to {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to add inline comment: {e}")
        return False


async def set_cursor_status(message: str, risk_level: str) -> bool:
    """Update Cursor's status bar with notification"""
    try:
        status_update = {
            "type": "neo_status_update",
            "message": message,
            "severity": risk_level.lower(),
            "icon": "⚠️" if risk_level != "LOW" else "ℹ️",
        }

        print(json.dumps(status_update))

        logger.debug(f"Status bar updated: {message}")
        return True

    except Exception as e:
        logger.error(f"Failed to update status bar: {e}")
        return False


async def handle_cursor_chat_response(
    user_choice: str,
    notification_id: str,
    conflicting_agent: str,
) -> Dict[str, Any]:
    """Handle user's response from Cursor chat"""

    choice_lower = user_choice.lower().strip()

    if "wait" in choice_lower or choice_lower == "1":
        return {
            "success": True,
            "action": "wait",
            "message": f"⏸ Pausing. Watching for {conflicting_agent}'s completion...",
            "polling_enabled": True,
            "poll_interval": 3,
        }

    elif "coordinate" in choice_lower or choice_lower == "2":
        return {
            "success": True,
            "action": "coordinate",
            "message": f"🤝 Sending coordination request to {conflicting_agent}...",
            "next_step": "await_confirmation",
        }

    elif "continue" in choice_lower or choice_lower == "3":
        return {
            "success": True,
            "action": "continue",
            "message": "✓ Proceeding with your changes. Watch for merge conflicts.",
            "warning": "Merge conflicts may occur during git operations.",
        }

    elif "override" in choice_lower or choice_lower == "4":
        return {
            "success": True,
            "action": "override",
            "message": "🚨 Override enabled. You take priority. Prepare for manual merge resolution.",
            "risk_level": "HIGH",
            "warning": "Manual conflict resolution will be required.",
        }

    else:
        return {
            "success": False,
            "error": f"Unknown choice: {user_choice}",
            "valid_options": ["wait", "coordinate", "continue", "override", "1", "2", "3", "4"],
        }


async def setup_cursor_watchers():
    """Setup file watchers for Cursor to detect conflicts in real-time"""

    setup_config = {
        "type": "neo_cursor_setup",
        "watchers": [
            {
                "pattern": "**/*.py",
                "events": ["change", "create", "delete"],
                "check_conflicts": True,
            },
            {
                "pattern": "**/*.ts",
                "events": ["change", "create", "delete"],
                "check_conflicts": True,
            },
            {
                "pattern": "**/*.js",
                "events": ["change", "create", "delete"],
                "check_conflicts": True,
            },
        ],
        "polling_interval_ms": 1000,
    }

    print(json.dumps(setup_config))
    logger.info("Cursor watchers setup initiated")


# Export main handler
handle_conflict_notification = OpenAIAdapter.handle_conflict_notification
