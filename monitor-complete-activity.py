#!/usr/bin/env python3
"""
Complete Neo Activity Monitor - displays ALL Neo metrics and data points
Shows: conflicts, impacts, staleness, locks, dependencies, and all other Neo capabilities
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import sys

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import get_active_entries, read_log, ACTIVITY_LOG_DIR
from core.risk_classifier import classify_risk, RiskLevel
from core.freshness import check_freshness, delta_since_base
from core.impact_alerts import ImpactAlertManager
from core.semantic_conflict_detector import SemanticAnalyzer
from core.cross_file_impact import CrossFileImpactAnalyzer


class CompleteNeoMonitor:
    """Monitor displaying ALL Neo capabilities and metrics"""

    def __init__(self, watch_interval: int = 2):
        self.watch_interval = watch_interval
        self.last_log_size = 0
        self.impact_manager = ImpactAlertManager()

    def format_timestamp(self, ts: float) -> str:
        """Format timestamp as readable string"""
        dt = datetime.fromtimestamp(ts)
        now = datetime.now()
        age = now - dt

        if age.total_seconds() < 60:
            return f"{int(age.total_seconds())}s ago"
        elif age.total_seconds() < 3600:
            return f"{int(age.total_seconds() / 60)}m ago"
        else:
            return dt.strftime("%H:%M:%S")

    def print_section(self, title: str, char: str = "═"):
        """Print section header"""
        print(f"\n{char * 80}")
        print(f"  {title}")
        print(f"{char * 80}\n")

    def print_subsection(self, title: str, char: str = "─"):
        """Print subsection header"""
        print(f"\n{char * 60}")
        print(f"  {title}")
        print(f"{char * 60}\n")

    def get_conflict_analysis(self, entry: Dict[str, Any], all_entries: List[Dict[str, Any]]) -> Optional[Dict]:
        """Analyze conflicts for an entry"""
        current_file = entry["file_path"]
        current_dev = entry["developer_id"]

        # Find other developers on same file
        conflicts = []
        for other in all_entries:
            if (other["developer_id"] != current_dev and
                other["file_path"] == current_file and
                abs(other["timestamp"] - entry["timestamp"]) < 1800):  # Within 30 min

                # Use risk classifier
                assessment = classify_risk(
                    current_dev,
                    current_file,
                    entry.get("intent", ""),
                    entry.get("region"),
                    other
                )

                conflicts.append({
                    "other_dev": other["developer_id"],
                    "other_intent": other.get("intent", "N/A"),
                    "other_region": other.get("region", "whole file"),
                    "risk_level": assessment.level.value,
                    "reason": assessment.reason,
                })

        return conflicts if conflicts else None

    def get_lock_status(self, entry: Dict[str, Any]) -> Optional[Dict]:
        """Extract lock information from entry"""
        if not entry.get("lock_state"):
            return None

        lock_info = {
            "state": entry.get("lock_state"),
            "holder": entry.get("lock_holder"),
            "scope": entry.get("lock_scope", "file"),
            "reason": entry.get("lock_reason", "UNKNOWN"),
            "queue_position": entry.get("queue_position"),
            "waiting_for": entry.get("waiting_for"),
        }

        # Add timing info
        if entry.get("lock_acquired_at"):
            lock_info["acquired_at"] = self.format_timestamp(entry["lock_acquired_at"])
        if entry.get("lock_expires_at"):
            expires = entry["lock_expires_at"]
            time_left = expires - time.time()
            if time_left > 0:
                lock_info["expires_in"] = f"{int(time_left // 60)}m {int(time_left % 60)}s"
            else:
                lock_info["expired"] = True

        return lock_info

    def get_staleness_analysis(self, entry: Dict[str, Any]) -> Optional[Dict]:
        """Check if developer's context is stale"""
        file_path = entry["file_path"]
        dev_id = entry["developer_id"]

        try:
            freshness = check_freshness(dev_id, file_path)

            if freshness == "CURRENT":
                return {"status": "CURRENT", "stale": False}
            elif freshness == "STALE_SOURCE":
                delta = delta_since_base(dev_id, file_path)
                return {
                    "status": "STALE_SOURCE",
                    "stale": True,
                    "changes": delta.split('\n') if delta else [],
                    "needs_refresh": True
                }
            else:
                return {"status": "UNVERIFIABLE", "note": "No baseline recorded"}
        except:
            return None

    def get_impact_analysis(self, entry: Dict[str, Any]) -> Optional[Dict]:
        """Analyze downstream and upstream impacts"""
        file_path = entry["file_path"]

        try:
            impacts = self.impact_manager.check_impacts_on_file(file_path)

            if impacts["has_impacts"]:
                alert_data = impacts.get("alerts", [])
                return {
                    "has_impacts": True,
                    "alert_count": len(alert_data),
                    "upstream_sources": list(set(a.get("source_file", "") for a in alert_data)),
                    "impact_reasons": [a.get("impact_reason", "") for a in alert_data],
                }
            else:
                return {"has_impacts": False}
        except:
            return None

    def get_semantic_analysis(self, entry: Dict[str, Any]) -> Optional[Dict]:
        """Analyze semantic symbols in file"""
        file_path = entry["file_path"]

        try:
            if not Path(file_path).exists():
                return None

            analyzer = SemanticAnalyzer(file_path)
            symbols = analyzer.extract_symbols()
            deps = analyzer.analyze_dependencies()

            return {
                "symbol_count": len(symbols),
                "symbols": [s.fully_qualified_name() for s in sorted(symbols, key=lambda x: x.name)],
                "dependency_count": len(deps),
                "dependency_types": list(set(d.type for d in deps)),
            }
        except:
            return None

    def get_agent_metadata(self, entry: Dict[str, Any]) -> Optional[Dict]:
        """Extract agent execution metadata"""
        metadata = entry.get("agent_metadata", {})
        if not metadata:
            return None

        return {
            "model": metadata.get("model"),
            "tokens_used": metadata.get("tokens_used"),
            "confidence": metadata.get("confidence"),
            "execution_time": metadata.get("execution_time"),
        }

    def format_entry_complete(self, entry: Dict[str, Any], all_entries: List[Dict[str, Any]]) -> str:
        """Format complete entry with ALL metrics"""
        output = []

        # Basic info
        dev_id = entry.get("developer_id", "UNKNOWN")
        file_path = entry.get("file_path", "UNKNOWN")
        intent = entry.get("intent", "")
        region = entry.get("region", "whole file")
        timestamp = entry.get("timestamp", 0)

        output.append(f"👤 DEVELOPER: {dev_id}")
        output.append(f"📄 FILE: {file_path}")
        output.append(f"⏰ TIME: {self.format_timestamp(timestamp)}")
        output.append(f"💭 INTENT: {intent[:80]}...")
        output.append(f"🎯 REGION: {region}")

        # Intent metadata
        if entry.get("intent_category"):
            output.append(f"📌 CATEGORY: {entry['intent_category']}")
        if entry.get("intent_scope"):
            output.append(f"📐 SCOPE: {entry['intent_scope']}")
        if entry.get("estimated_completion"):
            remaining = entry["estimated_completion"]
            output.append(f"⏳ ETA: {int(remaining / 60)}m remaining")
        if entry.get("blocking_others"):
            output.append(f"🚫 BLOCKING: Yes - other developers waiting")

        # ═══ CONFLICT DETECTION ═══
        conflicts = self.get_conflict_analysis(entry, all_entries)
        if conflicts:
            output.append("\n  ⚠️  CONFLICT DETECTION:")
            for conflict in conflicts:
                output.append(f"    • Conflicts with {conflict['other_dev']}")
                output.append(f"      Risk Level: {conflict['risk_level']} 🔴" if conflict['risk_level'] == 'HIGH'
                            else f"      Risk Level: {conflict['risk_level']} 🟡" if conflict['risk_level'] == 'MEDIUM'
                            else f"      Risk Level: {conflict['risk_level']} 🟢")
                output.append(f"      Reason: {conflict['reason']}")
                output.append(f"      Their Region: {conflict['other_region']}")
        else:
            output.append("\n  ✅ CONFLICT DETECTION: No conflicts detected")

        # ═══ LOCK STATUS ═══
        lock = self.get_lock_status(entry)
        if lock:
            output.append("\n  🔒 LOCK STATUS:")
            output.append(f"    • State: {lock['state']}")
            output.append(f"    • Holder: {lock['holder']}")
            output.append(f"    • Scope: {lock['scope']}")
            output.append(f"    • Reason: {lock['reason']}")
            if lock.get("queue_position") is not None:
                output.append(f"    • Queue Position: {lock['queue_position']} (0=next)")
            if lock.get("waiting_for"):
                output.append(f"    • Waiting For: {lock['waiting_for']}")
            if lock.get("expires_in"):
                output.append(f"    • Expires In: {lock['expires_in']}")
            if lock.get("acquired_at"):
                output.append(f"    • Acquired: {lock['acquired_at']}")

        # ═══ CONTEXT STALENESS ═══
        staleness = self.get_staleness_analysis(entry)
        if staleness:
            output.append("\n  🔄 CONTEXT STALENESS:")
            output.append(f"    • Status: {staleness['status']}")
            if staleness.get("stale"):
                output.append(f"    • ⚠️ STALE - Needs context refresh")
                if staleness.get("changes"):
                    output.append(f"    • Changed Symbols ({len(staleness['changes'])}):")
                    for change in staleness["changes"][:5]:
                        output.append(f"      - {change}")
                    if len(staleness["changes"]) > 5:
                        output.append(f"      ... and {len(staleness['changes']) - 5} more")

        # ═══ IMPACT ANALYSIS ═══
        impacts = self.get_impact_analysis(entry)
        if impacts:
            output.append("\n  📡 IMPACT ANALYSIS:")
            if impacts["has_impacts"]:
                output.append(f"    • UNRESOLVED IMPACTS: {impacts['alert_count']} 🔴")
                if impacts.get("upstream_sources"):
                    output.append(f"    • Upstream Sources: {', '.join(impacts['upstream_sources'])}")
                if impacts.get("impact_reasons"):
                    output.append(f"    • Impact Reasons:")
                    for reason in impacts["impact_reasons"][:3]:
                        output.append(f"      - {reason[:70]}")
            else:
                output.append(f"    • No unresolved impacts ✅")

        # ═══ SEMANTIC ANALYSIS ═══
        semantic = self.get_semantic_analysis(entry)
        if semantic:
            output.append("\n  🔤 SEMANTIC ANALYSIS:")
            output.append(f"    • Symbols in file: {semantic['symbol_count']}")
            if semantic["symbols"]:
                output.append(f"    • Functions/Classes:")
                for sym in semantic["symbols"][:8]:
                    output.append(f"      - {sym}")
                if len(semantic["symbols"]) > 8:
                    output.append(f"      ... and {len(semantic['symbols']) - 8} more")
            output.append(f"    • Dependencies tracked: {semantic['dependency_count']}")
            if semantic.get("dependency_types"):
                output.append(f"    • Dependency types: {', '.join(semantic['dependency_types'])}")

        # ═══ AGENT METADATA ═══
        agent = self.get_agent_metadata(entry)
        if agent:
            output.append("\n  🤖 AGENT EXECUTION:")
            if agent.get("model"):
                output.append(f"    • Model: {agent['model']}")
            if agent.get("tokens_used"):
                output.append(f"    • Tokens: {agent['tokens_used']}")
            if agent.get("confidence"):
                output.append(f"    • Confidence: {agent['confidence']:.2%}")
            if agent.get("execution_time"):
                output.append(f"    • Execution Time: {agent['execution_time']:.2f}s")

        # ═══ TENANT ISOLATION ═══
        if entry.get("tenant_id") and entry["tenant_id"] != "default":
            output.append(f"\n  🏢 TENANT: {entry['tenant_id']}")

        return "\n".join(output)

    def monitor(self, duration: int = 60):
        """Monitor and display all Neo activity"""
        print("\n")
        self.print_section("🔍 NEO COMPLETE ACTIVITY MONITOR - ALL METRICS", "═")
        print(f"Monitoring {ACTIVITY_LOG_DIR}/activity-log.json")
        print(f"Refresh interval: {self.watch_interval}s")
        print(f"Duration: {duration}s\n")

        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                entries = read_log()
                active = get_active_entries(expiry_minutes=30)

                if len(active) > self.last_log_size:
                    self.print_section(f"📊 NEO ACTIVITY LOG - {len(active)} Active Entries", "═")

                    # Group by developer
                    by_dev = {}
                    for entry in active:
                        dev = entry["developer_id"]
                        if dev not in by_dev:
                            by_dev[dev] = []
                        by_dev[dev].append(entry)

                    # Display each developer's activities
                    for dev_id in sorted(by_dev.keys()):
                        self.print_subsection(f"Developer: {dev_id}")
                        for entry in sorted(by_dev[dev_id], key=lambda x: x["timestamp"], reverse=True):
                            print(self.format_entry_complete(entry, active))
                            print("")

                    self.last_log_size = len(active)

                    # Summary stats
                    self.print_subsection("📈 SUMMARY STATISTICS")
                    print(f"Total Active Entries: {len(active)}")
                    print(f"Active Developers: {len(by_dev)}")

                    # Conflict summary
                    high_risk = sum(1 for e in active if e.get("blocking_others"))
                    print(f"Blocking Operations: {high_risk}")

                    # Lock summary
                    locked = sum(1 for e in active if e.get("lock_state") == "ACQUIRED")
                    waiting = sum(1 for e in active if e.get("lock_state") == "WAITING")
                    print(f"Files Locked: {locked}")
                    print(f"Developers Waiting: {waiting}")

                time.sleep(self.watch_interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Complete Neo Activity Monitor")
    parser.add_argument("--duration", type=int, default=120, help="Monitor duration in seconds")
    parser.add_argument("--interval", type=int, default=2, help="Refresh interval in seconds")

    args = parser.parse_args()

    monitor = CompleteNeoMonitor(watch_interval=args.interval)
    monitor.monitor(duration=args.duration)
