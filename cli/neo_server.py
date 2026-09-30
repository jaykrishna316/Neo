#!/usr/bin/env python3
"""Local Neo coordination server for multi-developer testing.

Runs a simple HTTP server that:
- Manages shared activity log (.devsync/activity-log.json)
- Detects conflicts via pre_gen_check
- Prints messages to terminal when conflicts occur
- Queues developers and manages lock promotion
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys
import threading
from datetime import datetime
from core.activity_log import log_activity, get_active_entries, read_log, clear_log
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel
from core.lock_manager import LockManager


class NeoServerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Neo server"""

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)

        if parsed.path == '/api/status':
            self._handle_status()
        elif parsed.path == '/api/activity':
            self._handle_get_activity()
        else:
            self._send_json(404, {'error': 'Not found'})

    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body) if body else {}

        if parsed.path == '/api/log-activity':
            self._handle_log_activity(data)
        elif parsed.path == '/api/check-conflicts':
            self._handle_check_conflicts(data)
        elif parsed.path == '/api/complete-work':
            self._handle_complete_work(data)
        elif parsed.path == '/api/reset-log':
            self._handle_reset_log(data)
        else:
            self._send_json(404, {'error': 'Not found'})

    def _handle_status(self):
        """GET /api/status - Server status"""
        response = {
            'status': 'ok',
            'server': 'Neo Local Server',
            'version': '4.0',
            'activity_log': str(Path('.devsync/activity-log.json')),
            'timestamp': datetime.now().isoformat()
        }
        self._send_json(200, response)

    def _handle_log_activity(self, data: Dict):
        """POST /api/log-activity - Log developer activity"""
        try:
            agent_id = data.get('agent_id')
            file_path = data.get('file_path')
            intent = data.get('intent')
            intent_category = data.get('intent_category', 'other')
            region = data.get('region')

            if not all([agent_id, file_path, intent]):
                self._send_json(400, {'error': 'Missing required fields'})
                return

            # Check for conflicts BEFORE logging
            risk_level, conflict_msg, _ = check_for_conflicts(
                agent_id=agent_id,
                file_path=file_path,
                intent=intent,
                region=region
            )

            # Initialize lock state for this developer
            lock_state = None
            lock_holder = None
            lock_acquired_at = None
            lock_expires_at = None
            lock_reason = None
            lock_scope = None
            queue_position = None
            waiting_for = None

            # If conflict detected, apply lock retroactively to FIRST developer
            if risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH):
                lock_manager = LockManager()
                lock_reason = "HIGH_CONFLICT" if risk_level == RiskLevel.HIGH else "MEDIUM_CONFLICT"
                lock_scope = "region" if region else "file"

                # Find first developer on this file
                existing_entries = [
                    e for e in get_active_entries()
                    if e.get('file_path') == file_path
                ]

                if existing_entries:
                    # Sort by timestamp to find first developer
                    first_entry = sorted(existing_entries, key=lambda x: x.get('timestamp', 0))[0]
                    first_developer = first_entry['developer_id']

                    # Acquire lock for FIRST developer (retroactively)
                    if first_developer != agent_id:
                        first_lock_info = lock_manager.acquire_lock(
                            file_path=file_path,
                            region=region,
                            developer_id=first_developer,
                            reason=lock_reason,
                            scope=lock_scope,
                        )

                        # Then queue current developer
                        current_lock_info = lock_manager.acquire_lock(
                            file_path=file_path,
                            region=region,
                            developer_id=agent_id,
                            reason=lock_reason,
                            scope=lock_scope,
                        )

                        # Current developer gets WAITING state
                        lock_state = current_lock_info.get('lock_state')
                        lock_holder = current_lock_info.get('lock_holder')
                        queue_position = current_lock_info.get('queue_position')
                        waiting_for = current_lock_info.get('waiting_for')

            # Log activity with lock state
            log_activity(
                developer_id=agent_id,
                file_path=file_path,
                intent=intent,
                intent_category=intent_category,
                region=region,
                lock_state=lock_state,
                lock_holder=lock_holder,
                lock_acquired_at=lock_acquired_at,
                lock_expires_at=lock_expires_at,
                lock_reason=lock_reason,
                lock_scope=lock_scope,
                queue_position=queue_position,
                waiting_for=waiting_for
            )

            # Get current state to show user
            entries = get_active_entries()
            # Count UNIQUE developers on this file (not entries)
            developers_on_file = set([e.get('developer_id') for e in entries if e.get('file_path') == file_path])
            same_file_count = len(developers_on_file)
            print(f"DEBUG: entries={[e.get('developer_id') for e in entries if e.get('file_path') == file_path]}, developers_on_file={developers_on_file}, same_file_count={same_file_count}")

            # Build response
            response = {
                'success': True,
                'message': f'✅ Logged: {intent}',
                'agent_id': agent_id,
                'file_path': file_path,
                'active_on_file': same_file_count,
                'risk_level': risk_level.value,
                'timestamp': datetime.now().isoformat()
            }

            # Show appropriate status message
            if risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH):
                self._print_lock_status(agent_id, file_path, lock_state, queue_position, waiting_for, risk_level)
            else:
                # No conflict - just log
                self._print_activity_log(agent_id, file_path, intent, same_file_count, lock_holder, queue_position, waiting_for)

            self._send_json(200, response)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_check_conflicts(self, data: Dict):
        """POST /api/check-conflicts - Check for conflicts"""
        try:
            agent_id = data.get('agent_id')
            file_path = data.get('file_path')
            intent = data.get('intent')
            region = data.get('region')

            if not all([agent_id, file_path, intent]):
                self._send_json(400, {'error': 'Missing required fields'})
                return

            # Check for conflicts
            risk_level, message, lock_info = check_for_conflicts(
                agent_id=agent_id,
                file_path=file_path,
                intent=intent,
                region=region
            )

            response = {
                'success': True,
                'risk_level': risk_level.value,
                'message': message,
                'should_block': risk_level == RiskLevel.HIGH,
                'should_warn': risk_level == RiskLevel.MEDIUM,
                'lock_info': lock_info,
                'agent_id': agent_id,
                'timestamp': datetime.now().isoformat()
            }

            # Print to terminal with icon
            self._print_conflict_check(agent_id, risk_level, message, lock_info)

            self._send_json(200, response)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_complete_work(self, data: Dict):
        """POST /api/complete-work - Mark work as complete and release lock"""
        try:
            agent_id = data.get('agent_id')
            file_path = data.get('file_path')
            lines_added = data.get('lines_added', 0)
            lines_removed = data.get('lines_removed', 0)

            if not all([agent_id, file_path]):
                self._send_json(400, {'error': 'Missing required fields'})
                return

            # Find active entry for this developer
            entries = get_active_entries()
            agent_entry = None
            for entry in entries:
                if entry.get('developer_id') == agent_id and entry.get('file_path') == file_path:
                    agent_entry = entry
                    break

            lock_released = False
            next_developer = None

            if agent_entry:
                # Mark work as complete
                lock_manager = LockManager()
                lock_manager.release_lock(file_path, None, agent_id)
                lock_released = True

                # Show completion message
                self._print_completion(agent_id, file_path, lines_added, lines_removed)

                # Promote next developer from queue
                lock_state = lock_manager.get_lock_state(file_path, None)
                if lock_state.get('queue_size', 0) > 0:
                    next_developer = lock_state.get('queue', [{}])[0].get('developer_id')

            response = {
                'success': True,
                'agent_id': agent_id,
                'file_path': file_path,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'lock_released': lock_released,
                'next_developer': next_developer,
                'timestamp': datetime.now().isoformat()
            }

            self._send_json(200, response)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_reset_log(self, data: Dict):
        """POST /api/reset-log - Clear activity log for new test"""
        try:
            entries = get_active_entries()
            entry_count = len(entries)

            clear_log()

            print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] Activity log reset")
            print(f"   Cleared {entry_count} entries")
            print(f"   Ready for new test\n")

            response = {
                'success': True,
                'entries_cleared': entry_count,
                'message': 'Activity log cleared',
                'timestamp': datetime.now().isoformat()
            }

            self._send_json(200, response)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_get_activity(self):
        """GET /api/activity - Get all activity"""
        try:
            entries = read_log()
            response = {
                'success': True,
                'entries': entries,
                'count': len(entries),
                'timestamp': datetime.now().isoformat()
            }
            self._send_json(200, response)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _send_json(self, status_code: int, data: Dict):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _print_activity_log(self, agent_id: str, file_path: str, intent: str, count: int, lock_holder: Optional[str] = None, queue_position: Optional[int] = None, waiting_for: Optional[str] = None):
        """Print activity to terminal"""
        icon = "✅" if count == 1 else "🔒"
        risk = "LOW" if count == 1 else "MEDIUM"
        print(f"\n{icon} [{datetime.now().strftime('%H:%M:%S')}] {agent_id} → {file_path}")
        print(f"   Intent: {intent}")
        print(f"   Risk: {risk} (developers on file: {count})")
        if count > 1:
            print(f"   ⚠️  Multiple developers detected. Lock applies.")
            if lock_holder or queue_position is not None:
                print(f"   🔒 Lock Status:")
                if lock_holder:
                    print(f"      Holder: {lock_holder}")
                if queue_position is not None:
                    print(f"      Queue Position: {queue_position}")
                if waiting_for:
                    print(f"      Waiting For: {waiting_for}")

    def _print_conflict_check(self, agent_id: str, risk_level: RiskLevel, message: str, lock_info: Optional[Dict]):
        """Print conflict check result to terminal"""
        if risk_level == RiskLevel.LOW:
            icon = "✅"
        elif risk_level == RiskLevel.MEDIUM:
            icon = "⚠️"
        else:
            icon = "🚫"

        print(f"\n{icon} [{datetime.now().strftime('%H:%M:%S')}] {agent_id} - Conflict Check")
        print(f"   Risk: {risk_level.value}")
        print(f"   {message}")

        if lock_info:
            print(f"   🔒 Lock Status:")
            print(f"      Holder: {lock_info.get('lock_holder')}")
            print(f"      Queue Position: {lock_info.get('queue_position', 'N/A')}")
            print(f"      Waiting For: {lock_info.get('waiting_for', 'N/A')}")

    def _print_lock_status(self, agent_id: str, file_path: str, lock_state: Optional[str],
                          queue_position: Optional[int], waiting_for: Optional[str], risk_level: RiskLevel):
        """Print lock status when activity is logged with lock state"""
        if risk_level == RiskLevel.MEDIUM:
            icon = "⚠️"
        else:
            icon = "🚫"

        print(f"\n{icon} [{datetime.now().strftime('%H:%M:%S')}] {agent_id} → {file_path}")

        if lock_state == "ACQUIRED":
            print(f"   ✅ Lock ACQUIRED - you are active on this file")
        elif lock_state == "WAITING":
            print(f"   ⏳ Lock WAITING - queued for this file")
            if queue_position is not None:
                print(f"      Queue Position: {queue_position}")
            if waiting_for:
                print(f"      Waiting for: {waiting_for}")

    def _print_completion(self, agent_id: str, file_path: str, lines_added: int, lines_removed: int):
        """Print completion message"""
        print(f"\n✅ [{datetime.now().strftime('%H:%M:%S')}] {agent_id} completed: +{lines_added} lines, -{lines_removed} lines")
        print(f"   File: {file_path}")
        print(f"   🔓 Lock released, promoting next developer")

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


class NeoServer:
    """Local Neo coordination server"""

    def __init__(self, host: str = 'localhost', port: int = 8000):
        self.host = host
        self.port = port
        self.server = HTTPServer((host, port), NeoServerHandler)
        self.log_file = Path('.devsync/activity-log.json')

    def start(self):
        """Start the server"""
        print("\n" + "="*60)
        print("🚀 Neo Local Coordination Server")
        print("="*60)
        print(f"\n📍 Server running at http://{self.host}:{self.port}")
        print(f"📝 Activity log: {self.log_file}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "="*60)
        print("Developers can now declare intent and check conflicts.")
        print("Messages will appear below.\n")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n\n" + "="*60)
            print("🛑 Server stopped")
            print("="*60 + "\n")


def run_server(host: str = 'localhost', port: int = 8000, clear: bool = False):
    """Run the Neo local server"""
    if clear:
        clear_log()

    server = NeoServer(host, port)
    server.start()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Neo Local Coordination Server')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8000, help='Server port')
    parser.add_argument('--clear', action='store_true', help='Clear activity log on startup')

    args = parser.parse_args()
    run_server(args.host, args.port, args.clear)
