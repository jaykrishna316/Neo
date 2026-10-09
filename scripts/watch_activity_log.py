#!/usr/bin/env python3
"""
Real-time Activity Log Watcher for Claude Terminals

Shows how Bob gets blocked and blocked when alice holds the lock.
Updates in real-time as activity log is written.
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime

LOG_FILE = Path(".devsync/activity-log.json")


def read_log():
    """Read activity log and return entries."""
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        entries = []
        for line in lines:
            if line.strip():
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    pass
        return entries
    except Exception:
        return []


def format_entry(entry):
    """Format an entry for display."""
    dev_id = entry.get("developer_id", "unknown")[:10].ljust(10)
    intent = entry.get("intent", "")[:60]
    lock_state = entry.get("lock_state", "")
    queue_pos = entry.get("queue_position")
    waiting = entry.get("waiting_for")

    # Mark blocks
    if lock_state == "WAITING":
        block_marker = "⏳ BLOCKED"
    elif lock_state == "ACQUIRED":
        block_marker = "🔒 LOCKED "
    else:
        block_marker = "          "

    status = ""
    if lock_state == "WAITING" and waiting:
        status = f" [waiting for {waiting}]"
    elif queue_pos is not None:
        status = f" [queue pos: {queue_pos}]"

    completed = entry.get("agent_metadata", {}).get("status") == "completed"
    if completed:
        lines = entry.get("agent_metadata", {})
        added = lines.get("lines_added", 0)
        removed = lines.get("lines_removed", 0)
        block_marker = "✅ DONE   "
        status = f" [+{added},-{removed}]"

    ts = entry.get("timestamp", 0)
    time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")

    return f"{time_str} | {block_marker} | {dev_id} | {intent}{status}"


def watch_log():
    """Watch activity log and display updates."""
    print("\n" + "="*120)
    print("NEO ACTIVITY LOG WATCHER - Real-time Coordination View")
    print("="*120)
    print("\nShowing where code is BLOCKED (⏳) and LOCKED (🔒):")
    print("  ⏳ BLOCKED = Developer waiting for another's lock")
    print("  🔒 LOCKED  = Developer holding the lock")
    print("  ✅ DONE    = Developer completed work")
    print("\n" + "-"*120)
    print(f"{'Time':<9} | {'Status':<10} | {'Developer':<10} | Intent & Status")
    print("-"*120 + "\n")

    last_count = 0

    try:
        while True:
            entries = read_log()
            current_count = len(entries)

            # Display new entries
            if current_count > last_count:
                for entry in entries[last_count:]:
                    print(format_entry(entry))
                last_count = current_count

            # Show summary
            if entries:
                locked = [e for e in entries if e.get("lock_state") == "ACQUIRED"]
                waiting = [e for e in entries if e.get("lock_state") == "WAITING"]
                completed = [e for e in entries if e.get("agent_metadata", {}).get("status") == "completed"]

                # Summary line
                summary = f"\n[SUMMARY] "
                if locked:
                    summary += f"🔒 {len(locked)} locked "
                if waiting:
                    summary += f"⏳ {len(waiting)} waiting "
                if completed:
                    summary += f"✅ {len(completed)} done"
                summary += f" | Total entries: {current_count}"

                # Only show summary when state changes
                if current_count > last_count:
                    print(summary)
                    print("-"*120)

            time.sleep(0.5)  # Check every 500ms for updates

    except KeyboardInterrupt:
        print("\n\n[Stopped]")
        sys.exit(0)


if __name__ == "__main__":
    watch_log()
