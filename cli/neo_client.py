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


class NeoClient:
    """Client for Neo coordination server"""

    def __init__(self, server_url: str = 'http://localhost:8000'):
        self.server_url = server_url

    def declare_intent(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
        intent_category: str = 'feature'
    ) -> Dict:
        """Declare intent to work on a file"""
        payload = {
            'agent_id': agent_id,
            'file_path': file_path,
            'intent': intent,
            'intent_category': intent_category,
            'region': region
        }

        try:
            response = requests.post(
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
            response = requests.post(
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
        lines_removed: int = 0
    ) -> Dict:
        """Mark work as complete and release lock"""
        payload = {
            'agent_id': agent_id,
            'file_path': file_path,
            'lines_added': lines_added,
            'lines_removed': lines_removed
        }

        try:
            response = requests.post(
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
            response = requests.post(
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
            response = requests.get(
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
            response = requests.get(
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


def print_response(data: Dict, action: str):
    """Pretty-print server response"""
    if 'error' in data:
        print(f"\n❌ Error: {data['error']}")
        if 'hint' in data:
            print(f"💡 {data['hint']}")
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

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # declare command
    declare_parser = subparsers.add_parser('declare', help='Declare intent on a file')
    declare_parser.add_argument('agent_id', help='Developer ID')
    declare_parser.add_argument('file_path', help='File path')
    declare_parser.add_argument('intent', help='What you intend to do')
    declare_parser.add_argument('--region', help='Specific region (optional)')
    declare_parser.add_argument('--category', default='feature', help='Intent category')

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

    client = NeoClient(args.server)

    if args.command == 'declare':
        result = client.declare_intent(
            args.agent_id,
            args.file_path,
            args.intent,
            args.region,
            args.category
        )
        print_response(result, 'declare')

    elif args.command == 'complete':
        result = client.complete_work(
            args.agent_id,
            args.file_path,
            args.added,
            args.removed
        )
        print_response(result, 'complete')

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
