#!/usr/bin/env python3
"""
Neo Activity Log Watcher
Real-time activity log monitor for multi-developer coordination testing.

Usage:
  Terminal 1: python3 watch_activity_log.py
  Terminal 2: python3 tests/devin_multi_agent_test.py alice
  Terminal 3: python3 tests/devin_multi_agent_test.py bob

The watcher will display updates to the activity log in real-time as developers work.
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def format_timestamp(ts: float) -> str:
    """Format Unix timestamp as HH:MM:SS."""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def get_entry_summary(entry: dict) -> str:
    """Create a one-line summary of an activity entry."""
    dev = entry.get("developer_id", "unknown")
    file = entry.get("file_path", "?").split("/")[-1]
    intent = entry.get("intent", "?")[:40]

    # Lock info
    lock = entry.get("lock_state", "")
    queue = entry.get("queue_position")
    waiting = entry.get("waiting_for", "")

    # Status
    status = (entry.get("agent_metadata") or {}).get("status", "active")

    # Timestamp
    ts = format_timestamp(entry.get("timestamp", time.time()))

    # Build summary
    summary = f"[{ts}] {dev:12} {file:15} {intent:40}"

    if lock:
        summary += f" [{lock}]"
    if queue is not None:
        summary += f" [Q:{queue}]"
    if waiting:
        summary += f" [Wait:{waiting}]"
    if status == "completed":
        summary += " [✓ DONE]"

    return summary


def watch_activity_log(log_path: Path = Path(".devsync/activity-log.json"), refresh_interval: float = 0.5):
    """
    Watch activity log for changes and display updates.

    Args:
        log_path: Path to activity log file
        refresh_interval: How often to check for updates (seconds)
    """

    print("\n" + "="*120)
    print("NEO ACTIVITY LOG WATCHER")
    print("="*120)
    print("Watching: " + str(log_path.absolute()))
    print("Refresh: Every {:.1f}s".format(refresh_interval))
    print("Ctrl-C to stop\n")

    last_entries = []
    entry_count = 0
    start_time = time.time()

    try:
        while True:
            # Read activity log
            entries = []
            if log_path.exists():
                try:
                    with open(log_path, "r") as f:
                        lines = f.readlines()

                    for line in lines:
                        if line.strip():
                            try:
                                data = eval(line.strip())
                                entries.append(data)
                            except:
                                pass
                except:
                    pass

            # Check if there are new entries
            if len(entries) != len(last_entries):
                # Show header
                clear_screen()
                elapsed = time.time() - start_time
                print("\n" + "="*120)
                print(f"NEO ACTIVITY LOG WATCHER - {format_timestamp(time.time())} (elapsed: {elapsed:.1f}s)")
                print("="*120)
                print()

                # Show stats
                devs = set(e.get("developer_id") for e in entries if e.get("developer_id"))
                completed = sum(1 for e in entries if (e.get("agent_metadata") or {}).get("status") == "completed")
                locked = sum(1 for e in entries if e.get("lock_state") in ("ACQUIRED", "WAITING"))
                waiting = sum(1 for e in entries if e.get("lock_state") == "WAITING")

                print(f"📊 Summary:")
                print(f"   Total entries: {len(entries)}")
                print(f"   Developers: {', '.join(sorted(devs)) if devs else 'none'}")
                print(f"   Completed: {completed}")
                print(f"   With locks: {locked} (waiting: {waiting})")
                print()

                # Show all entries
                print("📝 Activity Log:")
                print("-" * 120)
                for i, entry in enumerate(entries, 1):
                    summary = get_entry_summary(entry)
                    print(f"  {i:2}. {summary}")

                print("-" * 120)
                print()

                # Show lock state details
                lock_entries = [e for e in entries if e.get("lock_state")]
                if lock_entries:
                    print("🔒 Lock Details:")
                    for entry in lock_entries:
                        dev = entry.get("developer_id")
                        lock_state = entry.get("lock_state")
                        holder = entry.get("lock_holder")
                        reason = entry.get("lock_reason")
                        queue_pos = entry.get("queue_position")
                        waiting_for = entry.get("waiting_for")

                        if lock_state == "ACQUIRED":
                            print(f"   {dev:12} HOLDS lock (holder={holder}, reason={reason})")
                        elif lock_state == "WAITING":
                            print(f"   {dev:12} WAITS queue[{queue_pos}] for {waiting_for}")
                    print()

                last_entries = entries
                entry_count = len(entries)

            # Sleep before next check
            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\n\n✅ Watcher stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    watch_activity_log()
