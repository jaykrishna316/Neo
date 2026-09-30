#!/bin/bash
#
# Neo 3-Developer Demo Launcher
# Opens 7 Terminal windows for real-time coordination demo
# Terminal 1: Activity Log Viewer (monitoring)
# Terminal 2-4: Developers Alice, Bob, Charlie
# Terminal 5-7: Watchers Alice, Bob, Charlie
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
echo -e "${CYAN}║        NEO 3-DEVELOPER COORDINATION DEMO LAUNCHER              ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

# Make scripts executable
chmod +x "$NEO_DIR/bin/activity_log_viewer.sh"
chmod +x "$NEO_DIR/bin/developer_alice.sh"
chmod +x "$NEO_DIR/bin/developer_bob.sh"
chmod +x "$NEO_DIR/bin/developer_charlie.sh"
chmod +x "$NEO_DIR/bin/watcher_alice.sh"
chmod +x "$NEO_DIR/bin/watcher_bob.sh"
chmod +x "$NEO_DIR/bin/watcher_charlie.sh"

# Clean activity log
echo -e "${YELLOW}Cleaning activity log...${NC}"
rm -rf .devsync 2>/dev/null || true
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json

echo -e "${YELLOW}Opening 7 Terminal windows...${NC}\n"

# Open Terminal 1: Activity Log Viewer
echo -e "${BLUE}[1/7] Opening Activity Log Viewer${NC}"
open -a Terminal "$NEO_DIR/bin/activity_log_viewer.sh"
sleep 0.5

# Open Terminal 2: Developer Alice
echo -e "${BLUE}[2/7] Opening Developer Alice${NC}"
open -a Terminal "$NEO_DIR/bin/developer_alice.sh"
sleep 0.5

# Open Terminal 3: Developer Bob
echo -e "${BLUE}[3/7] Opening Developer Bob${NC}"
open -a Terminal "$NEO_DIR/bin/developer_bob.sh"
sleep 0.5

# Open Terminal 4: Developer Charlie
echo -e "${BLUE}[4/7] Opening Developer Charlie${NC}"
open -a Terminal "$NEO_DIR/bin/developer_charlie.sh"
sleep 0.5

# Open Terminal 5: Watcher Alice
echo -e "${BLUE}[5/7] Opening Watcher Alice${NC}"
open -a Terminal "$NEO_DIR/bin/watcher_alice.sh"
sleep 0.5

# Open Terminal 6: Watcher Bob
echo -e "${BLUE}[6/7] Opening Watcher Bob${NC}"
open -a Terminal "$NEO_DIR/bin/watcher_bob.sh"
sleep 0.5

# Open Terminal 7: Watcher Charlie
echo -e "${BLUE}[7/7] Opening Watcher Charlie${NC}"
open -a Terminal "$NEO_DIR/bin/watcher_charlie.sh"
sleep 0.5

echo ""
echo -e "${GREEN}✅ All 7 Terminal windows opened!${NC}"
echo ""
echo -e "${YELLOW}Demo Overview:${NC}"
echo -e "  ${CYAN}Terminal 1${NC} → Activity Log Viewer (shows real-time updates)"
echo -e "  ${CYAN}Terminal 2${NC} → Developer Alice (declares intent, checks conflicts, generates)"
echo -e "  ${CYAN}Terminal 3${NC} → Developer Bob (waits, gets context, generates)"
echo -e "  ${CYAN}Terminal 4${NC} → Developer Charlie (waits, gets context, generates)"
echo -e "  ${CYAN}Terminal 5${NC} → Watcher Alice (monitors Alice's conflicts)"
echo -e "  ${CYAN}Terminal 6${NC} → Watcher Bob (monitors Bob's queue position)"
echo -e "  ${CYAN}Terminal 7${NC} → Watcher Charlie (monitors Charlie's queue position)"
echo ""
echo -e "${YELLOW}Workflow Timeline:${NC}"
echo -e "  ${CYAN}T+0s${NC}   → Alice declares intent (LOW risk, no lock)"
echo -e "  ${CYAN}T+1s${NC}   → Bob declares intent (MEDIUM risk, gets queued)"
echo -e "  ${CYAN}T+2.5s${NC} → Charlie declares intent (MEDIUM risk, gets queued behind Bob)"
echo -e "  ${CYAN}T+4s${NC}   → Alice publishes code (lock released)"
echo -e "  ${CYAN}T+5s${NC}   → Bob gets fresh context and starts generating"
echo -e "  ${CYAN}T+7s${NC}   → Bob publishes code (lock released to Charlie)"
echo -e "  ${CYAN}T+8.5s${NC} → Charlie gets fresh context and starts generating"
echo -e "  ${CYAN}T+11.5s${NC} → Charlie publishes code"
echo ""
echo -e "${YELLOW}Close any terminal window to stop it independently.${NC}"
echo -e "${YELLOW}Ctrl-C in any terminal to exit gracefully.${NC}"
echo ""
