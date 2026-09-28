#!/usr/bin/env python3
"""File watcher for Neo - detects code changes and logs to server.

SECURITY: Requires explicit developer context via:
1. NEO_DEVELOPER environment variable (must match watcher's agent_id)
2. Prior intent declaration via CLI

This prevents accidental double-logging when multiple watchers are running.
"""

import sys
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Set, Optional
import hashlib
import requests
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import threading


class NeoFileWatcher(FileSystemEventHandler):
    """Watches for file changes and logs to Neo server with context validation"""

    def __init__(self, agent_id: str, server_url: str = 'http://localhost:8000', watched_patterns: Optional[List[str]] = None):
        self.agent_id = agent_id
        self.server_url = server_url
        self.watched_patterns = watched_patterns or ['src/**/*.py', 'lib/**/*.py']
        self.file_hashes: Dict[str, str] = {}
        self.last_logged: Dict[str, float] = {}
        self.min_interval = 5
        self.last_lock_state: Optional[str] = None
        self.monitoring = True

    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if file matches watched patterns
        if not self._should_watch(file_path):
            return

        # REQUIRED: Check NEO_DEVELOPER environment variable
        current_developer = os.getenv('NEO_DEVELOPER')
        if current_developer != self.agent_id:
            # Silently ignore - another developer's watcher should handle this
            return

        # Calculate file hash to detect actual changes
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                current_hash = hashlib.md5(content).hexdigest()
        except:
            return

        # Skip if file hasn't actually changed
        if self.file_hashes.get(str(file_path)) == current_hash:
            return

        self.file_hashes[str(file_path)] = current_hash

        # Rate limit
        now = time.time()
        if str(file_path) in self.last_logged:
            if now - self.last_logged[str(file_path)] < self.min_interval:
                return

        self.last_logged[str(file_path)] = now

        # Verify intent was declared (Option 2)
        if not self._verify_intent_declared(file_path):
            print(f"\n⚠️  [{datetime.now().strftime('%H:%M:%S')}] Edit blocked for {file_path}")
            print(f"   ❌ No intent declared by {self.agent_id}")
            print(f"   💡 Declare intent first: neo declare {self.agent_id} {file_path} '<intent>'")
            return

        # Log to server
        self._log_to_server(file_path)

    def _should_watch(self, file_path: Path) -> bool:
        """Check if file matches watched patterns"""
        return (
            any(p in str(file_path) for p in ['src/', 'lib/']) and
            str(file_path).endswith('.py')
        )

    def _verify_intent_declared(self, file_path: Path) -> bool:
        """Check if intent was declared for this file"""
        try:
            rel_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            rel_path = str(file_path)

        try:
            # Query server for active entries
            response = requests.get(
                f'{self.server_url}/api/activity',
                timeout=2
            )
            data = response.json()

            # Check if this developer has declared intent on this file
            if data.get('success'):
                entries = data.get('entries', [])
                for entry in entries:
                    if (entry.get('developer_id') == self.agent_id and
                        entry.get('file_path') == rel_path):
                        return True
            return False
        except:
            # If can't verify, allow (server might be down)
            return True

    def _log_to_server(self, file_path: Path):
        """Log file change to Neo server"""
        try:
            try:
                rel_path = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                rel_path = str(file_path)

            intent = f"Working on {rel_path}"

            payload = {
                'agent_id': self.agent_id,
                'file_path': rel_path,
                'intent': intent,
                'intent_category': 'edit'
            }

            response = requests.post(
                f'{self.server_url}/api/log-activity',
                json=payload,
                timeout=2
            )

            if response.status_code != 200:
                print(f"⚠️  Failed to log to server: {response.status_code}")

        except requests.exceptions.ConnectionError:
            print(f"⚠️  Cannot connect to Neo server at {self.server_url}")
        except Exception as e:
            print(f"⚠️  Error logging to server: {e}")

    def get_lock_status(self) -> Optional[Dict]:
        """Check current lock status for this developer"""
        try:
            response = requests.get(
                f'{self.server_url}/api/activity',
                timeout=2
            )
            data = response.json()

            if data.get('success'):
                entries = data.get('entries', [])
                # Find this developer's most recent entry
                for entry in reversed(entries):
                    if entry.get('developer_id') == self.agent_id:
                        return {
                            'lock_state': entry.get('lock_state'),
                            'queue_position': entry.get('queue_position'),
                            'waiting_for': entry.get('waiting_for'),
                            'lock_holder': entry.get('lock_holder')
                        }
            return None
        except:
            return None

    def monitor_promotions(self):
        """Background thread: poll for lock promotions"""
        while self.monitoring:
            try:
                status = self.get_lock_status()
                if status:
                    current_state = status.get('lock_state')

                    # Detect promotion: was WAITING, now ACQUIRED
                    if (self.last_lock_state == 'WAITING' and
                        current_state == 'ACQUIRED'):
                        print(f"\n✅ [{datetime.now().strftime('%H:%M:%S')}] {self.agent_id} - Lock Released!")
                        print(f"   🔓 You are now ACTIVE")
                        print(f"   Ready to proceed with editing.\n")

                    self.last_lock_state = current_state

                time.sleep(2)  # Poll every 2 seconds
            except:
                time.sleep(2)


def run_watcher(agent_id: str, server_url: str = 'http://localhost:8000', watched_dir: str = '.'):
    """Run the file watcher"""

    # Check for environment variable context
    current_dev = os.getenv('NEO_DEVELOPER')

    print("\n" + "="*60)
    print("👁️  Neo File Watcher")
    print("="*60)
    print(f"\n👤 Watcher Agent ID: {agent_id}")
    print(f"📍 Server: {server_url}")
    print(f"📂 Watching: {watched_dir}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if current_dev:
        if current_dev == agent_id:
            print(f"\n✅ Developer context: NEO_DEVELOPER={current_dev}")
            print("   File changes will be logged as this developer")
        else:
            print(f"\n⚠️  WARNING: NEO_DEVELOPER={current_dev} (watcher is for {agent_id})")
            print(f"   Watcher inactive until NEO_DEVELOPER={agent_id}")
    else:
        print(f"\n⚠️  WARNING: NEO_DEVELOPER not set!")
        print(f"   Set it to activate this watcher:")
        print(f"   export NEO_DEVELOPER={agent_id}")

    print("\n" + "="*60)
    print("REQUIRED: Declare intent before editing")
    print("="*60)
    print(f"\nBefore editing, run:")
    print(f"  neo declare {agent_id} src/auth.py 'Your intent here'")
    print("\nPress Ctrl+C to stop watcher.\n")

    watcher = NeoFileWatcher(agent_id, server_url)
    observer = Observer()
    observer.schedule(watcher, path=watched_dir, recursive=True)

    # Start background promotion monitor
    monitor_thread = threading.Thread(target=watcher.monitor_promotions, daemon=True)
    monitor_thread.start()

    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.monitoring = False
        observer.stop()
        print("\n\n" + "="*60)
        print("🛑 Watcher stopped")
        print("="*60 + "\n")

    observer.join()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Neo File Watcher (requires NEO_DEVELOPER environment variable)')
    parser.add_argument('agent_id', help='Developer ID this watcher monitors')
    parser.add_argument('--server', default='http://localhost:8000', help='Neo server URL')
    parser.add_argument('--dir', default='.', help='Directory to watch')

    args = parser.parse_args()
    run_watcher(args.agent_id, args.server, args.dir)
