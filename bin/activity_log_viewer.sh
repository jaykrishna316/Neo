#!/bin/bash
# Activity Log Viewer - Real-time activity monitor
# This script runs in its own Terminal window

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$NEO_DIR"

python3 << 'EOF'
import time
import json
import os

os.system('clear')
print('=' * 70)
print('📊 ACTIVITY LOG VIEWER')
print('=' * 70)
print()

while True:
    os.system('clear')
    print('=' * 70)
    print('📊 ACTIVITY LOG VIEWER (Updated: ' + time.strftime('%H:%M:%S') + ')')
    print('=' * 70)
    print()

    try:
        with open('.devsync/activity-log.json') as f:
            data = json.load(f)

        print(f'Total Entries: {len(data)}')
        print()

        if data:
            print('DEVELOPER ACTIVITY:')
            print()
            by_dev = {}
            for entry in data:
                dev = entry.get('developer_id')
                if dev not in by_dev:
                    by_dev[dev] = []
                by_dev[dev].append(entry)

            for dev in sorted(by_dev.keys()):
                latest = by_dev[dev][-1]
                lock = latest.get('lock_state', 'N/A')
                queue = latest.get('queue_position', '')
                file = latest.get('file_path', '')
                intent = latest.get('intent', '')

                print(f'  👤 {dev.upper()}')
                print(f'     📄 File: {file}')
                print(f'     💭 Intent: {intent}')
                print(f'     🔒 Lock State: {lock}', end='')
                if queue != '':
                    print(f' (Queue: {queue})', end='')
                print()
        else:
            print('⏳ Waiting for developer activity...')

        print()
        print('(Refreshing every 2 seconds - Ctrl-C to stop)')
    except Exception as e:
        print(f'Error: {e}')

    time.sleep(2)
EOF
