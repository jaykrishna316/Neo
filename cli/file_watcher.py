#!/usr/bin/env python3
"""File watcher for Neo - detects code changes and logs to server.

Watches for file modifications and automatically logs activity to the Neo server.
Developers specify their ID and file patterns, and changes are tracked in real-time.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Optional
import hashlib
import requests
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class NeoFileWatcher(FileSystemEventHandler):
    """Watches for file changes and logs to Neo server"""

    def __init__(self, agent_id: str, server_url: str = 'http://localhost:8000', watched_patterns: Optional[List[str]] = None):
        self.agent_id = agent_id
        self.server_url = server_url
        self.watched_patterns = watched_patterns or ['src/**/*.py', 'lib/**/*.py']
        self.file_hashes: Dict[str, str] = {}  # Track file hashes to detect actual changes
        self.last_logged: Dict[str, float] = {}  # Rate limiting
        self.min_interval = 5  # Minimum seconds between logs for same file

    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if file matches watched patterns
        if not self._should_watch(file_path):
            return

        # Calculate file hash to detect actual changes (avoid double-triggers)
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

        # Rate limit: don't log same file too frequently
        now = time.time()
        if str(file_path) in self.last_logged:
            if now - self.last_logged[str(file_path)] < self.min_interval:
                return

        self.last_logged[str(file_path)] = now

        # Log to server
        self._log_to_server(file_path)

    def _should_watch(self, file_path: Path) -> bool:
        """Check if file matches watched patterns"""
        # For now, watch Python files in src/ and lib/
        parts = str(file_path).split('/')
        return (
            any(p in str(file_path) for p in ['src/', 'lib/']) and
            str(file_path).endswith('.py')
        )

    def _log_to_server(self, file_path: Path):
        """Log file change to Neo server"""
        try:
            # Convert absolute path to relative
            try:
                rel_path = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                rel_path = str(file_path)

            # Default intent based on file
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


def run_watcher(agent_id: str, server_url: str = 'http://localhost:8000', watched_dir: str = '.'):
    """Run the file watcher"""

    print("\n" + "="*60)
    print("👁️  Neo File Watcher")
    print("="*60)
    print(f"\n👤 Agent ID: {agent_id}")
    print(f"📍 Server: {server_url}")
    print(f"📂 Watching: {watched_dir}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nFile changes will be automatically logged.")
    print("Press Ctrl+C to stop.\n")

    watcher = NeoFileWatcher(agent_id, server_url)
    observer = Observer()
    observer.schedule(watcher, path=watched_dir, recursive=True)

    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n\n" + "="*60)
        print("🛑 Watcher stopped")
        print("="*60 + "\n")

    observer.join()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Neo File Watcher')
    parser.add_argument('agent_id', help='Developer ID')
    parser.add_argument('--server', default='http://localhost:8000', help='Neo server URL')
    parser.add_argument('--dir', default='.', help='Directory to watch')

    args = parser.parse_args()
    run_watcher(args.agent_id, args.server, args.dir)
