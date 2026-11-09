# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Jayakrishna Ichapurapu
# module-id: 12d07a5e-71f1baaf
import json

# Simulate what happens on second call
entries = json.loads(open('.devsync/activity-log.json').read())

file_path = 'src/auth.py'

# Current code (should work):
developers_on_file = set([e.get('developer_id') for e in entries if e.get('file_path') == file_path])
print(f"Unique developers (via set): {len(developers_on_file)} - {developers_on_file}")

# Old buggy code (counts entries):
all_entries = len([e for e in entries if e.get('file_path') == file_path])
print(f"Total entries (old buggy way): {all_entries}")
