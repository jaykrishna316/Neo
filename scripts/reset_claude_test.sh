#!/usr/bin/env bash
# Resets the Claude Code Neo test: starting files and Neo state.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf .neo_state .devsync/activity-log.json
mkdir -p src test-scenarios/services
printf 'def authenticate(user):\n    return False\n' > src/auth.py
printf 'from auth import authenticate\n\ndef pay(user):\n    return authenticate(user)\n' > test-scenarios/services/payment.py

echo "Reset done. Restart both Claude sessions before running the test."
