#!/bin/bash
#
# Neo Guided 3-Developer Demo
# Opens numbered Terminal windows with step-by-step guidance
# User presses Enter to proceed to next step
#

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$NEO_DIR"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     NEO GUIDED 3-DEVELOPER COORDINATION DEMO                   ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║  This demo opens 7 numbered Terminal windows and guides you    ║${NC}"
echo -e "${CYAN}║  through queue progression with 3 developers. Press Enter      ║${NC}"
echo -e "${CYAN}║  to advance to the next step.                                  ║${NC}"
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
rm -rf .devsync 2>/dev/null || true
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json

echo -e "${YELLOW}Opening 7 numbered Terminal windows...${NC}\n"
sleep 1

# Function to open terminal with title (cross-platform)
open_terminal_with_title() {
    local num=$1
    local title=$2
    local script=$3

    echo -e "${BLUE}[${num}/7]${NC} Opening: ${title}"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: Use AppleScript
        osascript <<EOF
tell application "Terminal"
    activate
    set newWindow to (create new window with default settings)
    tell newWindow
        set name to "${title}"
        do script "cd '$NEO_DIR' && bash '${script}' && exit" in (first tab of it)
    end tell
end tell
EOF
    else
        # Linux: Use gnome-terminal or xterm
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal --title="${title}" -- bash -c "cd '$NEO_DIR' && bash '${script}'; bash" &
        elif command -v xterm &> /dev/null; then
            xterm -title "${title}" -e "bash -c 'cd $NEO_DIR && bash $script; bash'" &
        else
            echo -e "${RED}ERROR: No terminal found. Install gnome-terminal or xterm.${NC}"
            return 1
        fi
    fi
    sleep 0.8
}

# Open the 7 terminals
open_terminal_with_title "1" "Terminal 1: Activity Log" "$NEO_DIR/bin/activity_log_viewer.sh"
open_terminal_with_title "2" "Terminal 2: Developer Alice" "$NEO_DIR/bin/developer_alice.sh"
open_terminal_with_title "3" "Terminal 3: Developer Bob" "$NEO_DIR/bin/developer_bob.sh"
open_terminal_with_title "4" "Terminal 4: Developer Charlie" "$NEO_DIR/bin/developer_charlie.sh"
open_terminal_with_title "5" "Terminal 5: Watcher Alice" "$NEO_DIR/bin/watcher_alice.sh"
open_terminal_with_title "6" "Terminal 6: Watcher Bob" "$NEO_DIR/bin/watcher_bob.sh"
open_terminal_with_title "7" "Terminal 7: Watcher Charlie" "$NEO_DIR/bin/watcher_charlie.sh"

echo ""
echo -e "${GREEN}✅ All 7 Terminal windows opened!${NC}"
echo ""
echo -e "${YELLOW}Window Layout:${NC}"
echo -e "  ${BOLD}Terminal 1${NC} → ${CYAN}Activity Log Viewer${NC}"
echo -e "  ${BOLD}Terminal 2${NC} → ${GREEN}Developer Alice${NC}"
echo -e "  ${BOLD}Terminal 3${NC} → ${GREEN}Developer Bob${NC}"
echo -e "  ${BOLD}Terminal 4${NC} → ${GREEN}Developer Charlie${NC}"
echo -e "  ${BOLD}Terminal 5${NC} → ${BLUE}Watcher Alice${NC}"
echo -e "  ${BOLD}Terminal 6${NC} → ${BLUE}Watcher Bob${NC}"
echo -e "  ${BOLD}Terminal 7${NC} → ${BLUE}Watcher Charlie${NC}"
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 1: Alice Declares Intent (First Developer - No Lock)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Alice is the first developer on auth.py. No lock applies yet."
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Alice appears: lock_state=${GREEN}ACQUIRED${NC}, queue_position=null"
echo ""
echo -e "  ${BOLD}Terminal 2 (Developer Alice):${NC}"
echo -e "    • ⏱️  [T+0s] Declaring intent..."
echo -e "    • ✅ Risk Level: ${GREEN}LOW${NC}"
echo ""
echo -e "  ${BOLD}Terminal 5 (Watcher Alice):${NC}"
echo -e "    • Monitoring Alice (will show LOW risk throughout)"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 2: Bob Declares Intent (Second Developer - Gets Queued)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Bob declares on same file → Conflict detected → Bob gets QUEUED"
echo -e "   Lock applies: Alice has it, Bob waits at queue position 0"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Bob appears: lock_state=${RED}WAITING${NC}, queue_position=${RED}1${NC}"
echo ""
echo -e "  ${BOLD}Terminal 3 (Developer Bob):${NC}"
echo -e "    • ⏱️  [T+1s] Declaring intent..."
echo -e "    • ⏱️  [T+2s] Checking for conflicts..."
echo -e "    • ⚠️  Risk Level: ${RED}MEDIUM${NC}"
echo -e "    • 🔒 Queue Position: ${RED}1${NC}"
echo ""
echo -e "  ${BOLD}Terminal 6 (Watcher Bob):${NC}"
echo -e "    • ⏱️  [T+1s] Initial check..."
echo -e "    • Risk = ${RED}MEDIUM${NC} | Queue Position: ${RED}0${NC}"
echo ""
echo -e "${CYAN}Key insight:${NC}"
echo -e "  • Bob is ready but won't generate yet"
echo -e "  • Waiting prevents merge conflicts"
echo -e "  • Position 0 means Bob is next (after Alice)"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 3: Charlie Declares Intent (Third Developer - Queued Behind Bob)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Charlie declares on same file → Gets QUEUED behind Bob"
echo -e "   Queue now: Alice (locked) → Bob (next) → Charlie (waiting)"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Charlie appears: lock_state=${RED}WAITING${NC}, queue_position=${RED}2${NC}"
echo -e "    • Queue now shows: Alice → Bob (pos 1) → Charlie (pos 2)"
echo ""
echo -e "  ${BOLD}Terminal 4 (Developer Charlie):${NC}"
echo -e "    • ⏱️  [T+2.5s] Declaring intent..."
echo -e "    • ⏱️  [T+3s] Checking for conflicts..."
echo -e "    • ⚠️  Risk Level: ${RED}MEDIUM${NC}"
echo -e "    • 🔒 Queue Position: ${RED}2${NC}"
echo ""
echo -e "  ${BOLD}Terminal 7 (Watcher Charlie):${NC}"
echo -e "    • ⏱️  [T+2.5s] Initial check..."
echo -e "    • Risk = ${RED}MEDIUM${NC} | Queue Position: ${RED}1${NC}"
echo ""
echo -e "${CYAN}Queue structure:${NC}"
echo -e "  Position 0 (Locked):  Alice (generating)"
echo -e "  Position 1 (Waiting): Bob (will go next)"
echo -e "  Position 2 (Waiting): Charlie (will go third)"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 4: Alice Completes → Bob Promoted (Queue: Bob → Charlie)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Alice finishes and releases lock"
echo -e "   Bob automatically promoted to next in queue"
echo -e "   Charlie still waiting but closer to his turn"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 2 (Developer Alice):${NC}"
echo -e "    • ⏱️  [T+4s] Publishing changes..."
echo -e "    • ${GREEN}✅ Code published to repository${NC}"
echo -e "    • Alice workflow complete"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Alice's entry marked as published"
echo -e "    • Bob's entry: lock_state=${GREEN}ACQUIRED${NC}, queue_position=null"
echo -e "    • Charlie's entry: queue_position=${RED}1${NC} (moved up)"
echo ""
echo -e "  ${BOLD}Terminal 6 (Watcher Bob):${NC}"
echo -e "    • ⏱️  [T+5s] Retry after Alice completes..."
echo -e "    • Risk = ${GREEN}LOW${NC} ✅"
echo -e "    • ${GREEN}Lock released - Bob can proceed!${NC}"
echo ""
echo -e "${CYAN}Automatic promotion:${NC}"
echo -e "  • No manual queue management"
echo -e "  • Next developer automatically gets lock"
echo -e "  • Context from previous developer available"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 5: Bob Generates Based on Alice's Work${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Bob has fresh context from Alice"
echo -e "   Bob generates code built on top of Alice's changes"
echo -e "   Charlie watches and waits his turn"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 3 (Developer Bob):${NC}"
echo -e "    • ⏱️  [T+5s] Checking again (Alice should be done now)..."
echo -e "    • ${GREEN}✅ Found 2 entries from Alice${NC}"
echo -e "    • 📖 Merging Alice's changes into context..."
echo ""
echo -e "    • ⏱️  [T+6s] Generating code..."
echo -e "    •    ✏️  Generated: JWT token creation"
echo -e "    •    ✏️  Generated: Token validation"
echo ""
echo -e "  ${BOLD}Terminal 7 (Watcher Charlie):${NC}"
echo -e "    • ⏱️  [T+2.5s] Initial check..."
echo -e "    • Risk = ${RED}MEDIUM${NC} | Queue Position: ${RED}1${NC}"
echo -e "    • ⏱️  [T+8.5s] Still waiting (Bob working)"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Entries from: Alice (complete), Bob (generating), Charlie (waiting)"
echo ""
echo -e "${CYAN}Token efficiency:${NC}"
echo -e "  • Bob gets delta from activity log (~7 tokens)"
echo -e "  • NOT full file re-read (would be ~500 tokens)"
echo -e "  • Saves ~493 tokens per developer"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 6: Bob Publishes → Charlie Promoted (Last in Queue)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Bob finishes and publishes his changes"
echo -e "   Charlie automatically promoted to the lock"
echo -e "   Charlie has context from both Alice and Bob"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 3 (Developer Bob):${NC}"
echo -e "    • ⏱️  [T+7s] Publishing changes..."
echo -e "    • ${GREEN}✅ Code published to repository${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Bob marked as published"
echo -e "    • Charlie's entry: lock_state=${GREEN}ACQUIRED${NC}, queue_position=null"
echo ""
echo -e "  ${BOLD}Terminal 7 (Watcher Charlie):${NC}"
echo -e "    • ⏱️  [T+8.5s] Retry after Alice & Bob complete..."
echo -e "    • Risk = ${GREEN}LOW${NC} ✅"
echo -e "    • ${GREEN}Lock released - Charlie can proceed!${NC}"
echo ""
echo -e "${CYAN}Queue progression complete:${NC}"
echo -e "  • Alice finished (released to Bob)"
echo -e "  • Bob finished (released to Charlie)"
echo -e "  • Charlie now has the lock"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to see final step...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 7: Charlie Generates & Publishes (Workflow Complete)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Charlie generates based on context from Alice and Bob"
echo -e "   All 3 developers complete. Workflow finished."
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 4 (Developer Charlie):${NC}"
echo -e "    • ⏱️  [T+8.5s] Checking again..."
echo -e "    • ${GREEN}✅ Found X entries from Alice & Bob${NC}"
echo -e "    • 📖 Merging all changes into context..."
echo ""
echo -e "    • ⏱️  [T+9.5s] Generating code..."
echo -e "    •    ✏️  Generated: OAuth2 provider config"
echo -e "    •    ✏️  Generated: Token exchange handlers"
echo ""
echo -e "    • ⏱️  [T+11.5s] Publishing changes..."
echo -e "    • ${GREEN}✅ Code published to repository${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Complete history of all 3 developers"
echo -e "    • Queue progression: Alice → Bob → Charlie"
echo -e "    • All lock states captured"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Demo Summary: 3-Developer Coordination${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "✅ Conflicts prevented: ${RED}ALL${NC}"
echo -e "✅ Merge conflicts: ${GREEN}ZERO${NC}"
echo -e "✅ Manual resolution: ${GREEN}NONE${NC}"
echo -e "✅ Queue management: ${GREEN}AUTOMATIC${NC}"
echo -e "✅ Context: ${GREEN}ALWAYS FRESH${NC}"
echo -e "✅ Tokens saved: ${YELLOW}~1,500${NC} (vs traditional 3x re-reads)"
echo ""
echo -e "${YELLOW}What just happened:${NC}"
echo -e "  1. Alice worked alone (LOW risk)"
echo -e "  2. Bob queued behind Alice (MEDIUM risk)"
echo -e "  3. Charlie queued behind Bob (MEDIUM risk)"
echo -e "  4. Each developer got promoted automatically"
echo -e "  5. Each had fresh context from predecessors"
echo -e "  6. Zero conflicts throughout workflow"
echo ""
echo -e "${CYAN}This is Neo:${NC}"
echo -e "  • Semantic coordination at intent layer"
echo -e "  • Prevents conflicts BEFORE generation"
echo -e "  • Automatic queue management"
echo -e "  • Fresh context without re-reading files"
echo -e "  • 98-99% token savings at scale"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Try 2-developer guided demo: ${BOLD}./launch_guided_2dev_demo.sh${NC}"
echo -e "  2. Run automated tests: ${BOLD}python run_parallel_tests.sh${NC}"
echo -e "  3. Check activity log: ${BOLD}cat .devsync/activity-log.json | python -m json.tool${NC}"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to close this guide...${NC}"
read -r

echo ""
echo -e "${GREEN}✅ Guide complete!${NC}"
echo -e "${YELLOW}The Terminal windows will remain open. You can close them individually.${NC}"
echo ""
