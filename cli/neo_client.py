#!/usr/bin/env python3
"""Neo CLI client for local development testing.

Allows developers to:
- Declare intent on files
- Check for conflicts
- View activity log
- Query server status
"""

import sys
import json
import requests
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import os
import subprocess


class NeoClient:
    """Client for Neo coordination server"""

    def __init__(self, server_url: str = 'http://localhost:8000', api_token: Optional[str] = None):
        self.server_url = server_url
        self.session = requests.Session()
        # Token is only needed when the server runs with one (e.g. behind ngrok).
        # The ngrok header skips its browser warning page for API clients.
        token = api_token or os.getenv('NEO_API_TOKEN')
        if token:
            self.session.headers['Authorization'] = f'Bearer {token}'
        self.session.headers['ngrok-skip-browser-warning'] = 'true'

    def declare_intent(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
        intent_category: str = 'feature',
        snapshot: Optional[Dict] = None
    ) -> Dict:
        """Declare intent to work on a file. `snapshot` is {commit, file_hash} of the
        developer's working copy, used to validate their context at hand-off."""
        payload = {
            'agent_id': agent_id,
            'file_path': file_path,
            'intent': intent,
            'intent_category': intent_category,
            'region': region,
            'snapshot': snapshot
        }

        try:
            response = self.session.post(
                f'{self.server_url}/api/log-activity',
                json=payload,
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {
                'error': f'Cannot connect to Neo server at {self.server_url}',
                'hint': 'Make sure the server is running: neo server --local'
            }
        except Exception as e:
            return {'error': str(e)}

    def reset_log(self) -> Dict:
        """Clear the activity log (reset test)"""
        try:
            response = self.session.post(
                f'{self.server_url}/api/reset-log',
                json={},
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {
                'error': f'Cannot connect to Neo server at {self.server_url}',
                'hint': 'Make sure the server is running'
            }
        except Exception as e:
            return {'error': str(e)}

    def complete_work(
        self,
        agent_id: str,
        file_path: str,
        lines_added: int = 0,
        lines_removed: int = 0,
        summary: Optional[str] = None,
        diff: Optional[str] = None,
        commit: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> Dict:
        """Mark work as complete, release lock, and hand off to the next developer"""
        payload = {
            'agent_id': agent_id,
            'file_path': file_path,
            'lines_added': lines_added,
            'lines_removed': lines_removed,
            'summary': summary,
            'diff': diff,
            'commit': commit,
            'file_hash': file_hash
        }

        try:
            response = self.session.post(
                f'{self.server_url}/api/complete-work',
                json=payload,
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {
                'error': f'Cannot connect to Neo server at {self.server_url}',
                'hint': 'Make sure the server is running'
            }
        except Exception as e:
            return {'error': str(e)}

    def check_conflicts(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None
    ) -> Dict:
        """Check for conflicts before proceeding"""
        payload = {
            'agent_id': agent_id,
            'file_path': file_path,
            'intent': intent,
            'region': region
        }

        try:
            response = self.session.post(
                f'{self.server_url}/api/check-conflicts',
                json=payload,
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {
                'error': f'Cannot connect to Neo server at {self.server_url}',
                'hint': 'Make sure the server is running: neo server --local'
            }
        except Exception as e:
            return {'error': str(e)}

    def get_activity(self) -> Dict:
        """Get all activity from log"""
        try:
            response = self.session.get(
                f'{self.server_url}/api/activity',
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {
                'error': f'Cannot connect to Neo server at {self.server_url}',
                'hint': 'Make sure the server is running: neo server --local'
            }
        except Exception as e:
            return {'error': str(e)}

    def get_status(self) -> Dict:
        """Get server status"""
        try:
            response = self.session.get(
                f'{self.server_url}/api/status',
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {
                'error': f'Cannot connect to Neo server at {self.server_url}',
                'hint': 'Make sure the server is running: neo server --local'
            }
        except Exception as e:
            return {'error': str(e)}

    def get_inbox(self, agent_id: str, unread_only: bool = False) -> Dict:
        """Notifications for this developer"""
        try:
            response = self.session.get(
                f'{self.server_url}/api/inbox',
                params={'agent_id': agent_id, 'unread': '1' if unread_only else '0'},
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {'error': f'Cannot connect to Neo server at {self.server_url}'}
        except Exception as e:
            return {'error': str(e)}

    def ack_inbox(self, agent_id: str, event_ids: list) -> Dict:
        """Mark notifications as read"""
        try:
            response = self.session.post(
                f'{self.server_url}/api/inbox/ack',
                json={'agent_id': agent_id, 'event_ids': event_ids},
                timeout=5
            )
            return response.json()
        except Exception as e:
            return {'error': str(e)}

    def refresh_context(self, agent_id: str, file_path: str, repo_dir: str = '.') -> Dict:
        """Pull the latest code, then confirm the working copy matches the reset context.

        The server refuses further declare/complete on the file until the file on disk
        matches the version the hand-off recorded. If git pull fails, nothing is confirmed.
        """
        try:
            pull = subprocess.run(
                ['git', 'pull', '--ff-only'], cwd=repo_dir,
                capture_output=True, text=True, timeout=60
            )
        except FileNotFoundError:
            return {'error': 'git not found on PATH'}
        if pull.returncode != 0:
            return {
                'error': 'git pull failed; context not refreshed',
                'hint': pull.stderr.strip() or pull.stdout.strip(),
            }

        snap = repo_snapshot(file_path, repo_dir)
        try:
            response = self.session.post(
                f'{self.server_url}/api/refresh-context',
                json={'agent_id': agent_id, 'file_path': file_path,
                      'commit': snap['commit'], 'file_hash': snap['file_hash']},
                timeout=5
            )
            data = response.json()
            data['git_pull'] = pull.stdout.strip()
            return data
        except Exception as e:
            return {'error': str(e)}

    def get_file_session(self, file_path: str) -> Dict:
        """Base commit and every contribution to this file in the current session"""
        try:
            response = self.session.get(
                f'{self.server_url}/api/file-session',
                params={'file_path': file_path},
                timeout=5
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            return {'error': f'Cannot connect to Neo server at {self.server_url}'}
        except Exception as e:
            return {'error': str(e)}


def _git_out(args: list, repo_dir: str = '.') -> Optional[str]:
    """Stdout of a git command, stripped. None if git fails or is missing."""
    try:
        result = subprocess.run(['git', *args], cwd=repo_dir, capture_output=True,
                                text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def repo_snapshot(file_path: str, repo_dir: str = '.') -> Dict:
    """The working copy's state: HEAD commit and sha256 of the file's content"""
    path = Path(repo_dir) / file_path
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    return {'commit': _git_out(['rev-parse', 'HEAD'], repo_dir), 'file_hash': file_hash}


def hand_off_problem(file_path: str, repo_dir: str = '.') -> Optional[str]:
    """Why this developer cannot hand off yet, or None if they can.

    The next developer pulls from the remote, so the work must be committed and pushed.
    """
    if _git_out(['rev-parse', '--is-inside-work-tree'], repo_dir) is None:
        return f"{repo_dir} is not a git repository. Run complete from your clone."
    if _git_out(['status', '--porcelain', '--', file_path], repo_dir):
        return f"{file_path} has uncommitted changes. Commit them before completing."
    if not _git_out(['branch', '-r', '--contains', 'HEAD'], repo_dir):
        return "Your latest commit is not pushed. Push it so the next developer can pull it."
    return None


def build_changes_report(session: Dict, file_path: str, repo_dir: str = '.') -> str:
    """Combined changes to the file from the session base, with each contribution attributed"""
    contributions = session.get('contributions', [])
    if not contributions:
        return f"No changes recorded for {file_path} yet."

    _git_out(['fetch', '--quiet'], repo_dir)  # best effort: make other developers' commits visible

    base = session.get('base_commit')
    last = contributions[-1].get('commit')
    devs = []
    for c in contributions:
        if c['developer'] not in devs:
            devs.append(c['developer'])

    lines = [f"Changes to {file_path} ({session.get('status', 'open')} session)",
             f"Developers: {', '.join(devs)}", ""]

    if base and last:
        overall = _git_out(['diff', base, last, '--', file_path], repo_dir)
        lines.append(f"Overall, from {base[:8]} to {last[:8]}:")
        lines.append(overall or "(no net change to the file)")
    else:
        lines.append("Overall: git history unavailable here; contributions below.")
    lines.append("")

    prev = base
    for i, c in enumerate(contributions, 1):
        lines.append(f"--- {i}. {c['developer']}: {c.get('summary') or '(no summary)'}")
        step = None
        if prev and c.get('commit'):
            step = _git_out(['diff', prev, c['commit'], '--', file_path], repo_dir)
        lines.append(step or c.get('diff') or "(no diff recorded)")
        lines.append("")
        prev = c.get('commit') or prev
    return "\n".join(lines)


def git_diff(file_path: str, max_chars: int = 8000, repo_dir: str = '.') -> Optional[str]:
    """Diff of one file for the hand-off: uncommitted changes if any, else the last commit
    that touched it. Truncated. None if git is unavailable or there is no change."""
    commands = [
        ['git', 'diff', 'HEAD', '--', file_path],
        ['git', 'show', '--format=', 'HEAD', '--', file_path],
    ]
    for cmd in commands:
        try:
            result = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout[:max_chars]
    return None


def print_response(data: Dict, action: str):
    """Pretty-print server response"""
    if 'error' in data:
        print(f"\n❌ Error: {data['error']}")
        if 'message' in data:
            print(f"   {data['message']}")
        if 'hint' in data:
            print(f"💡 {data['hint']}")
        return

    if action == 'inbox':
        events = data.get('events', [])
        if not events:
            print(f"\n📭 No notifications for {data.get('agent_id')}")
            return
        print(f"\n📬 Notifications for {data.get('agent_id')} ({len(events)})")
        for e in events:
            flag = '' if e.get('read') else ' [NEW]'
            print(f"\n  • {e['type']}{flag} from {e['from']} on {e['file_path']}")
            print(f"    {e['message']}")
            if e.get('summary'):
                print(f"    Summary: {e['summary']}")
            if e.get('context_expired'):
                print(f"    ♻️  Your context had expired and was reset to {e['from']}'s version")
            if e.get('refresh_required') and not e.get('acknowledged'):
                print(f"    ⚠️  Refresh required: run 'refresh' before continuing")
        return

    if action == 'refresh':
        if not data.get('refreshed'):
            print(f"\n✅ {data.get('message', 'Nothing to refresh')}")
            return
        print(f"\n🔁 Context refreshed for {data.get('file_path')}")
        if data.get('context_expired'):
            print(f"   ♻️  Context had expired and was reset")
        print(f"   Changes from: {data.get('from')}")
        print(f"   Summary: {data.get('summary') or 'none provided'}")
        if data.get('diff'):
            print(f"\n{data['diff']}")
        return

    if action == 'declare':
        print(f"\n✅ Intent Declared")
        print(f"   Developer: {data.get('agent_id')}")
        print(f"   File: {data.get('file_path')}")
        print(f"   Developers on file: {data.get('active_on_file', 0)}")
        if data.get('active_on_file', 0) > 1:
            print(f"   ⚠️  Multiple developers - lock applies!")

    elif action == 'check':
        risk = data.get('risk_level', 'UNKNOWN')
        if risk == 'LOW':
            icon = "✅"
        elif risk == 'MEDIUM':
            icon = "⚠️"
        else:
            icon = "🚫"

        print(f"\n{icon} Conflict Check Result")
        print(f"   Risk: {risk}")
        print(f"   {data.get('message', 'No message')}")

        if data.get('lock_info'):
            lock = data['lock_info']
            print(f"\n   🔒 Lock Status:")
            print(f"      Holder: {lock.get('lock_holder', 'N/A')}")
            print(f"      Queue Position: {lock.get('queue_position', 'N/A')}")
            print(f"      Waiting For: {lock.get('waiting_for', 'N/A')}")

    elif action == 'complete':
        if data.get('error'):
            print(f"\n❌ Error: {data['error']}")
        else:
            print(f"\n✅ Work Completed")
            print(f"   Developer: {data.get('agent_id', 'unknown')}")
            print(f"   File: {data.get('file_path', 'unknown')}")
            print(f"   Changes: +{data.get('lines_added', 0)} lines, -{data.get('lines_removed', 0)} lines")
            if data.get('lock_released'):
                print(f"   🔓 Lock released, next developer promoted")

    elif action == 'reset':
        if data.get('error'):
            print(f"\n❌ Error: {data['error']}")
        else:
            print(f"\n🔄 Activity Log Reset")
            print(f"   ✅ Cleared {data.get('entries_cleared', 0)} entries")
            print(f"   Ready to start new test without restarting server/watchers")

    elif action == 'status':
        print(f"\n✅ Neo Server Status")
        print(f"   Status: {data.get('status', 'unknown')}")
        print(f"   Version: {data.get('version', 'unknown')}")
        print(f"   Activity Log: {data.get('activity_log', 'unknown')}")

    elif action == 'log':
        entries = data.get('entries', [])
        print(f"\n📝 Activity Log ({len(entries)} entries)")
        for entry in entries:
            ts = entry.get('timestamp', 'unknown')
            dev = entry.get('developer_id', 'unknown')
            file = entry.get('file_path', 'unknown')
            intent = entry.get('intent', 'no intent')
            print(f"   [{ts}] {dev} → {file}")
            print(f"      {intent}")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Neo Local Coordination Client')
    parser.add_argument('--server', default='http://localhost:8000', help='Server URL')
    parser.add_argument('--token', default=None,
                        help='API token for the server (default: $NEO_API_TOKEN, if set)')

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # declare command
    declare_parser = subparsers.add_parser('declare', help='Declare intent on a file')
    declare_parser.add_argument('agent_id', help='Developer ID')
    declare_parser.add_argument('file_path', help='File path')
    declare_parser.add_argument('intent', help='What you intend to do')
    declare_parser.add_argument('--region', help='Specific region (optional)')
    declare_parser.add_argument('--category', default='feature', help='Intent category')
    declare_parser.add_argument('--repo', default='.', help='Your git clone (default: current directory)')

    # check command
    check_parser = subparsers.add_parser('check', help='Check for conflicts')
    check_parser.add_argument('agent_id', help='Developer ID')
    check_parser.add_argument('file_path', help='File path')
    check_parser.add_argument('intent', help='What you intend to do')
    check_parser.add_argument('--region', help='Specific region (optional)')

    # complete command
    complete_parser = subparsers.add_parser('complete', help='Mark work as complete')
    complete_parser.add_argument('agent_id', help='Developer ID')
    complete_parser.add_argument('file_path', help='File path')
    complete_parser.add_argument('--added', type=int, default=0, help='Lines added')
    complete_parser.add_argument('--removed', type=int, default=0, help='Lines removed')
    complete_parser.add_argument('--summary', default=None, help='Summary of your change (sent to the other developers)')
    complete_parser.add_argument('--no-diff', action='store_true', help="Don't attach the git diff of the file")
    complete_parser.add_argument('--repo', default='.', help='Your git clone (default: current directory)')

    # changes command
    changes_parser = subparsers.add_parser('changes', help='Combined changes to a file, with each developer attributed')
    changes_parser.add_argument('file_path', help='File path')
    changes_parser.add_argument('--repo', default='.', help='Your git clone (default: current directory)')

    # inbox command
    inbox_parser = subparsers.add_parser('inbox', help='Show notifications for a developer')
    inbox_parser.add_argument('agent_id', help='Developer ID')
    inbox_parser.add_argument('--unread', action='store_true', help='Only unread notifications')

    # refresh command
    refresh_parser = subparsers.add_parser('refresh', help='Pull latest code and refresh context after a hand-off')
    refresh_parser.add_argument('agent_id', help='Developer ID')
    refresh_parser.add_argument('file_path', help='File path')
    refresh_parser.add_argument('--repo', default='.', help='Git repo directory (default: current)')

    # reset command
    reset_parser = subparsers.add_parser('reset', help='Reset activity log (clear test)')

    # log command
    log_parser = subparsers.add_parser('log', help='View activity log')

    # status command
    status_parser = subparsers.add_parser('status', help='Check server status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    client = NeoClient(args.server, api_token=args.token)

    if args.command == 'declare':
        result = client.declare_intent(
            args.agent_id,
            args.file_path,
            args.intent,
            args.region,
            args.category,
            snapshot=repo_snapshot(args.file_path, args.repo)
        )
        print_response(result, 'declare')

    elif args.command == 'complete':
        problem = hand_off_problem(args.file_path, args.repo)
        if problem:
            print(f"\n🚫 Cannot complete yet: {problem}")
            return
        snap = repo_snapshot(args.file_path, args.repo)
        diff = None if args.no_diff else git_diff(args.file_path, repo_dir=args.repo)
        result = client.complete_work(
            args.agent_id,
            args.file_path,
            args.added,
            args.removed,
            summary=args.summary,
            diff=diff,
            commit=snap['commit'],
            file_hash=snap['file_hash']
        )
        print_response(result, 'complete')

    elif args.command == 'changes':
        session = client.get_file_session(args.file_path)
        if session.get('error'):
            print_response(session, 'changes')
        elif not session.get('session'):
            print(f"\nNo changes recorded for {args.file_path} yet.")
        else:
            print("\n" + build_changes_report(session['session'], args.file_path, args.repo))

    elif args.command == 'inbox':
        result = client.get_inbox(args.agent_id, unread_only=args.unread)
        print_response(result, 'inbox')
        events = result.get('events', [])
        unread_ids = [e['id'] for e in events if not e.get('read')]
        if unread_ids:
            client.ack_inbox(args.agent_id, unread_ids)

    elif args.command == 'refresh':
        result = client.refresh_context(args.agent_id, args.file_path, args.repo)
        print_response(result, 'refresh')

    elif args.command == 'reset':
        result = client.reset_log()
        print_response(result, 'reset')

    elif args.command == 'check':
        result = client.check_conflicts(
            args.agent_id,
            args.file_path,
            args.intent,
            args.region
        )
        print_response(result, 'check')

    elif args.command == 'log':
        result = client.get_activity()
        print_response(result, 'log')

    elif args.command == 'status':
        result = client.get_status()
        print_response(result, 'status')


if __name__ == '__main__':
    main()
