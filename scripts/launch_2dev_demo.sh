#!/bin/bash
#
# Neo 2-Developer Demo Launcher
# Opens 5 Terminal windows for real-time coordination demo
# Terminal 1: Activity Log Viewer (monitoring)
# Terminal 2: Developer Alice
# Terminal 3: Developer Bob
# Terminal 4: Watcher Alice
# Terminal 5: Watcher Bob
#

set -e

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$NEO_DIR"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        NEO 2-DEVELOPER COORDINATION DEMO LAUNCHER              ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

# Make scripts executable
chmod +x "$NEO_DIR/bin/activity_log_viewer.sh"
chmod +x "$NEO_DIR/bin/developer_alice.sh"
chmod +x "$NEO_DIR/bin/developer_bob.sh"
chmod +x "$NEO_DIR/bin/watcher_alice.sh"
chmod +x "$NEO_DIR/bin/watcher_bob.sh"

# Clean activity log
echo -e "${YELLOW}Cleaning activity log...${NC}"
rm -rf .devsync 2>/dev/null || true
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json

echo -e "${YELLOW}Opening 5 Terminal windows...${NC}\n"

# Open Terminal 1: Activity Log Viewer
echo -e "${BLUE}[1/5] Opening Activity Log Viewer${NC}"
open -a Terminal "$NEO_DIR/bin/activity_log_viewer.sh"
sleep 0.5

# Open Terminal 2: Developer Alice
echo -e "${BLUE}[2/5] Opening Developer Alice${NC}"
open -a Terminal "$NEO_DIR/bin/developer_alice.sh"
sleep 0.5

# Open Terminal 3: Developer Bob
echo -e "${BLUE}[3/5] Opening Developer Bob${NC}"
open -a Terminal "$NEO_DIR/bin/developer_bob.sh"
sleep 0.5

# Open Terminal 4: Watcher Alice
echo -e "${BLUE}[4/5] Opening Watcher Alice${NC}"
open -a Terminal "$NEO_DIR/bin/watcher_alice.sh"
sleep 0.5

# Open Terminal 5: Watcher Bob
echo -e "${BLUE}[5/5] Opening Watcher Bob${NC}"
open -a Terminal "$NEO_DIR/bin/watcher_bob.sh"
sleep 0.5

echo ""
echo -e "${GREEN}✅ All 5 Terminal windows opened!${NC}"
echo ""
echo -e "${YELLOW}Demo Overview:${NC}"
echo -e "  ${CYAN}Terminal 1${NC} → Activity Log Viewer (shows real-time updates)"
echo -e "  ${CYAN}Terminal 2${NC} → Developer Alice (declares intent, checks conflicts, generates)"
echo -e "  ${CYAN}Terminal 3${NC} → Developer Bob (waits, gets context, generates)"
echo -e "  ${CYAN}Terminal 4${NC} → Watcher Alice (monitors Alice's conflicts)"
echo -e "  ${CYAN}Terminal 5${NC} → Watcher Bob (monitors Bob's queue position)"
echo ""
echo -e "${YELLOW}Workflow Timeline:${NC}"
echo -e "  ${CYAN}T+0s${NC}  → Alice declares intent (LOW risk, no lock)"
echo -e "  ${CYAN}T+1s${NC}  → Bob declares intent (MEDIUM risk, gets queued)"
echo -e "  ${CYAN}T+4s${NC}  → Alice publishes code (lock released)"
echo -e "  ${CYAN}T+5s${NC}  → Bob gets fresh context from Alice's changes"
echo -e "  ${CYAN}T+7s${NC}  → Bob publishes code"
echo ""
echo -e "${YELLOW}Close any terminal window to stop it independently.${NC}"
echo -e "${YELLOW}Ctrl-C in any terminal to exit gracefully.${NC}"
echo ""
