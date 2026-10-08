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
import hmac
import os
import secrets
import signal
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
from core import workflow_events
from cli.ngrok_tunnel import NgrokError, start_ngrok_tunnel, stop_ngrok_tunnel


class NeoServerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Neo server"""

    # Set by NeoServer. When None, requests are not authenticated (localhost use).
    # When set (e.g. when exposed through ngrok), every request needs a matching
    # 'Authorization: Bearer <token>' header.
    api_token: Optional[str] = None

    def _is_authorized(self) -> bool:
        """Check the bearer token, if one is configured"""
        if not self.api_token:
            return True
        header = self.headers.get('Authorization', '')
        prefix = 'Bearer '
        if not header.startswith(prefix):
            return False
        return hmac.compare_digest(header[len(prefix):], self.api_token)

    def do_GET(self):
        """Handle GET requests"""
        if not self._is_authorized():
            self._send_json(401, {'error': 'Unauthorized: missing or invalid API token'})
            return

        parsed = urlparse(self.path)

        if parsed.path == '/api/status':
            self._handle_status()
        elif parsed.path == '/api/activity':
            self._handle_get_activity()
        elif parsed.path == '/api/inbox':
            self._handle_get_inbox(parse_qs(parsed.query))
        elif parsed.path == '/api/file-session':
            self._handle_get_file_session(parse_qs(parsed.query))
        else:
            self._send_json(404, {'error': 'Not found'})

    def do_POST(self):
        """Handle POST requests"""
        if not self._is_authorized():
            self._send_json(401, {'error': 'Unauthorized: missing or invalid API token'})
            return

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
        elif parsed.path == '/api/inbox/ack':
            self._handle_ack_inbox(data)
        elif parsed.path == '/api/refresh-context':
            self._handle_refresh_context(data)
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

            # Must refresh context after a hand-off before declaring on this file again
            pending = workflow_events.pending_refresh(agent_id, file_path)
            if pending:
                self._send_json(409, {
                    'error': 'Refresh required',
                    'message': f"{pending['from']} finished {file_path}. "
                               f"Run 'refresh' before declaring intent on it.",
                })
                return

            # Check for conflicts BEFORE logging (also acquires locks if needed)
            risk_level, conflict_msg, lock_info = check_for_conflicts(
                agent_id=agent_id,
                file_path=file_path,
                intent=intent,
                region=region
            )

            # Extract lock state from check_for_conflicts result
            lock_state = None
            lock_holder = None
            lock_acquired_at = None
            lock_expires_at = None
            lock_reason = None
            lock_scope = None
            queue_position = None
            waiting_for = None

            # Use lock info from check_for_conflicts (locks already acquired there)
            if lock_info:
                lock_holder = lock_info.get('lock_holder')
                queue_position = lock_info.get('queue_position')
                waiting_for = lock_info.get('waiting_for')
                lock_state = "ACQUIRED" if lock_holder == agent_id else "WAITING"

            # Remember what this developer's context was built on (commit + file hash)
            snapshot = data.get('snapshot') or {}
            if snapshot:
                workflow_events.set_context(agent_id, file_path, snapshot.get('commit'),
                                            snapshot.get('file_hash'))
                if lock_state == "ACQUIRED":
                    workflow_events.open_session_if_needed(file_path, snapshot.get('commit'),
                                                           snapshot.get('file_hash'))

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
                # Print full conflict check message with lock status
                self._print_conflict_check(agent_id, risk_level, conflict_msg, lock_info)
            else:
                # No conflict - just log activity
                self._print_activity_log(agent_id, file_path, intent, same_file_count, lock_holder, queue_position, waiting_for)

            self._send_json(200, response)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_check_conflicts(self, data: Dict):
        """POST /api/check-conflicts - Check for conflicts (no lock acquisition here)"""
        try:
            agent_id = data.get('agent_id')
            file_path = data.get('file_path')
            intent = data.get('intent')
            region = data.get('region')

            if not all([agent_id, file_path, intent]):
                self._send_json(400, {'error': 'Missing required fields'})
                return

            # Get active entries for this file
            active_entries = get_active_entries()
            same_file_entries = [
                e for e in active_entries
                if e.get('file_path') == file_path and e.get('developer_id') != agent_id
            ]

            # Simple risk assessment (without lock acquisition)
            if not same_file_entries:
                risk_level = RiskLevel.LOW
                message = "No conflicting work detected. Safe to proceed."
                lock_info = None
            else:
                risk_level = RiskLevel.MEDIUM
                other_devs = [e.get('developer_id') for e in same_file_entries]
                message = f"MEDIUM RISK: {', '.join(other_devs)} working on {file_path}. Overlapping regions detected. Proceed with caution."
                lock_info = None

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
        """POST /api/complete-work - Finish coding: release lock, hand off, record contribution"""
        try:
            agent_id = data.get('agent_id')
            file_path = data.get('file_path')
            lines_added = data.get('lines_added', 0)
            lines_removed = data.get('lines_removed', 0)
            summary = data.get('summary') or ''
            diff = data.get('diff')
            commit = data.get('commit')
            file_hash = data.get('file_hash')

            if not all([agent_id, file_path]):
                self._send_json(400, {'error': 'Missing required fields'})
                return

            pending = workflow_events.pending_refresh(agent_id, file_path)
            if pending:
                self._send_json(409, {
                    'error': 'Refresh required',
                    'message': f"{pending['from']} finished {file_path}. "
                               f"Run 'refresh' before completing your work on it.",
                })
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
                lock_manager = LockManager()
                release = lock_manager.release_lock(file_path, None, agent_id)
                lock_released = release.get('success', False)
                next_developer = release.get('next_lock_holder')

                self._print_completion(agent_id, file_path, lines_added, lines_removed)
                self._record_handoff(agent_id, file_path, summary, diff, commit, file_hash, next_developer)

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

    def _record_handoff(self, completer: str, file_path: str, summary: str,
                        diff: Optional[str], commit: Optional[str], file_hash: Optional[str],
                        next_developer: Optional[str]):
        """Record the completer's contribution, validate and reset the next developer's
        context, and send the notifications."""
        base = workflow_events.get_context(completer, file_path) or {}
        workflow_events.open_session_if_needed(file_path, base.get('commit'), base.get('file_hash'))
        session = workflow_events.add_contribution(
            file_path, completer, commit, file_hash, summary, diff
        )
        on_top_of_others = len(session['contributions']) > 1

        if next_developer and next_developer != completer:
            expired = workflow_events.validate_and_reset_context(
                next_developer, file_path, commit, file_hash
            )
            status = ("Your context had expired and has been reset to " if expired
                      else "Your context is still valid and has been reset to ")
            workflow_events.record_event(
                to=next_developer, from_dev=completer, event_type=workflow_events.LOCK_GRANTED,
                file_path=file_path,
                message=f"{completer} finished {file_path}. {status}{completer}'s version. "
                        f"Run 'refresh' before you continue.",
                summary=summary, diff=diff, refresh_required=True,
                context_expired=expired, file_hash_value=file_hash,
            )
            print(f"   📬 {next_developer} notified: {completer} is done, context "
                  f"{'expired and reset' if expired else 'reset'}, refresh required")
        else:
            workflow_events.close_session(file_path)

        others = workflow_events.participants(
            file_path, exclude={completer, next_developer or ''}
        )
        for dev in sorted(others):
            message = (f"{completer} submitted updates on top of your changes to {file_path}."
                       if on_top_of_others else f"{completer} finished {file_path}.")
            workflow_events.record_event(
                to=dev, from_dev=completer, event_type=workflow_events.WORK_COMPLETED,
                file_path=file_path, message=message, summary=summary, diff=diff,
            )
            print(f"   📬 {dev} notified: {completer} finished")

    def _handle_get_inbox(self, query: Dict):
        """GET /api/inbox?agent_id=...&unread=1 - Developer's notifications"""
        try:
            agent_id = query.get('agent_id', [None])[0]
            if not agent_id:
                self._send_json(400, {'error': 'Missing agent_id'})
                return
            unread_only = query.get('unread', ['0'])[0] in ('1', 'true')
            events = workflow_events.get_inbox(agent_id, unread_only=unread_only)
            self._send_json(200, {'success': True, 'agent_id': agent_id,
                                  'events': events, 'count': len(events)})
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_get_file_session(self, query: Dict):
        """GET /api/file-session?file_path=... - Base commit and every contribution in order"""
        try:
            file_path = query.get('file_path', [None])[0]
            if not file_path:
                self._send_json(400, {'error': 'Missing file_path'})
                return
            session = workflow_events.get_session(file_path)
            self._send_json(200, {'success': True, 'file_path': file_path, 'session': session})
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_ack_inbox(self, data: Dict):
        """POST /api/inbox/ack - Mark notifications as read"""
        try:
            agent_id = data.get('agent_id')
            event_ids = data.get('event_ids', [])
            if not agent_id:
                self._send_json(400, {'error': 'Missing agent_id'})
                return
            changed = workflow_events.mark_read(agent_id, event_ids)
            self._send_json(200, {'success': True, 'marked_read': changed})
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _handle_refresh_context(self, data: Dict):
        """POST /api/refresh-context - Confirm the working copy matches the reset context.

        Refused unless the file on disk has the same hash as the version the hand-off
        reset the context to, so a pull that did not bring the changes cannot clear the block.
        """
        try:
            agent_id = data.get('agent_id')
            file_path = data.get('file_path')
            commit = data.get('commit')
            file_hash = data.get('file_hash')
            if not all([agent_id, file_path]):
                self._send_json(400, {'error': 'Missing required fields'})
                return

            pending = workflow_events.pending_refresh(agent_id, file_path)
            if pending is None:
                self._send_json(200, {'success': True, 'refreshed': False,
                                      'message': 'Nothing to refresh for this file'})
                return

            if file_hash != pending.get('file_hash'):
                self._send_json(409, {
                    'error': 'Refresh incomplete',
                    'message': f"Your copy of {file_path} does not match {pending['from']}'s version. "
                               f"Pull the latest changes and try again.",
                })
                return

            workflow_events.set_context(agent_id, file_path, commit, file_hash)
            workflow_events.acknowledge_refresh(agent_id, file_path)
            session = workflow_events.get_session(file_path) or {}
            print(f"\n🔁 [{datetime.now().strftime('%H:%M:%S')}] {agent_id} refreshed context for {file_path}")
            self._send_json(200, {
                'success': True,
                'refreshed': True,
                'from': pending['from'],
                'file_path': file_path,
                'summary': pending['summary'],
                'diff': pending['diff'],
                'context_expired': pending['context_expired'],
                'contributions': len(session.get('contributions', [])),
            })
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

    def __init__(self, host: str = 'localhost', port: int = 8000,
                 api_token: Optional[str] = None, use_ngrok: bool = False):
        self.host = host
        self.port = port
        self.api_token = api_token
        self.use_ngrok = use_ngrok
        self.public_url: Optional[str] = None
        NeoServerHandler.api_token = api_token
        self.server = HTTPServer((host, port), NeoServerHandler)
        self.log_file = Path('.devsync/activity-log.json')

    def start(self):
        """Start the server"""
        ngrok_proc = None
        if self.use_ngrok:
            try:
                ngrok_proc, self.public_url = start_ngrok_tunnel(self.port)
            except NgrokError as e:
                print(f"\n❌ {e}")
                self.server.server_close()
                return

            # Treat SIGTERM like Ctrl+C so the ngrok child is always cleaned up
            def _interrupt(signum, frame):
                raise KeyboardInterrupt
            signal.signal(signal.SIGTERM, _interrupt)

        print("\n" + "="*60)
        print("🚀 Neo Local Coordination Server")
        print("="*60)
        print(f"\n📍 Server running at http://{self.host}:{self.port}")
        if self.public_url:
            print(f"🌐 Public URL (ngrok): {self.public_url}")
        if self.api_token:
            print(f"🔑 API token required on every request: {self.api_token}")
            print("   Send as header: Authorization: Bearer <token>")
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
        finally:
            if ngrok_proc is not None:
                stop_ngrok_tunnel(ngrok_proc)


def run_server(host: str = 'localhost', port: int = 8000, clear: bool = False,
               api_token: Optional[str] = None, use_ngrok: bool = False):
    """Run the Neo local server

    Args:
        api_token: Require this bearer token on every request. Falls back to the
                   NEO_API_TOKEN env var.
        use_ngrok: Expose the server through an ngrok tunnel. Implies a token:
                   one is generated if none is supplied.
    """
    if clear:
        clear_log()

    token = api_token or os.getenv('NEO_API_TOKEN') or None
    if use_ngrok and not token:
        token = secrets.token_urlsafe(16)

    server = NeoServer(host, port, api_token=token, use_ngrok=use_ngrok)
    server.start()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Neo Local Coordination Server')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8000, help='Server port')
    parser.add_argument('--clear', action='store_true', help='Clear activity log on startup')
    parser.add_argument('--token', default=None,
                        help='Require this API token (default: $NEO_API_TOKEN, if set)')
    parser.add_argument('--ngrok', action='store_true',
                        help='Expose the server via an ngrok tunnel (requires the ngrok CLI). '
                             'Generates a token if none is set.')

    args = parser.parse_args()
    run_server(args.host, args.port, args.clear, api_token=args.token, use_ngrok=args.ngrok)
