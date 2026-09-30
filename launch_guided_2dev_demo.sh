#!/bin/bash
#
# Neo Guided 2-Developer Demo
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
echo -e "${CYAN}║     NEO GUIDED 2-DEVELOPER COORDINATION DEMO                   ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║  This demo opens 5 numbered Terminal windows and guides you    ║${NC}"
echo -e "${CYAN}║  through each step. Press Enter to advance to the next step.   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

# Make scripts executable
chmod +x "$NEO_DIR/bin/activity_log_viewer.sh"
chmod +x "$NEO_DIR/bin/developer_alice.sh"
chmod +x "$NEO_DIR/bin/developer_bob.sh"
chmod +x "$NEO_DIR/bin/watcher_alice.sh"
chmod +x "$NEO_DIR/bin/watcher_bob.sh"

# Clean activity log
rm -rf .devsync 2>/dev/null || true
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json

echo -e "${YELLOW}Opening 5 numbered Terminal windows...${NC}\n"
sleep 1

# Function to open terminal with title
open_terminal_with_title() {
    local num=$1
    local title=$2
    local script=$3

    echo -e "${BLUE}[${num}/5]${NC} Opening: ${title}"

    # Create a wrapper script that sets terminal title
    cat > /tmp/neo_demo_$num.sh << 'WRAPPER'
#!/bin/bash
SCRIPT_PATH="$1"
TITLE="$2"
# Set terminal title
echo -ne "\033]0;${TITLE}\007"
# Run the script
bash "$SCRIPT_PATH"
WRAPPER
    chmod +x /tmp/neo_demo_$num.sh
    open -a Terminal /tmp/neo_demo_$num.sh "$script" "$title"
    sleep 0.8
}

# Open the 5 terminals
open_terminal_with_title "1" "Terminal 1: Activity Log Viewer" "$NEO_DIR/bin/activity_log_viewer.sh"
open_terminal_with_title "2" "Terminal 2: Developer Alice" "$NEO_DIR/bin/developer_alice.sh"
open_terminal_with_title "3" "Terminal 3: Developer Bob" "$NEO_DIR/bin/developer_bob.sh"
open_terminal_with_title "4" "Terminal 4: Watcher Alice" "$NEO_DIR/bin/watcher_alice.sh"
open_terminal_with_title "5" "Terminal 5: Watcher Bob" "$NEO_DIR/bin/watcher_bob.sh"

echo ""
echo -e "${GREEN}✅ All 5 Terminal windows opened!${NC}"
echo ""
echo -e "${YELLOW}Window Layout:${NC}"
echo -e "  ${BOLD}Terminal 1${NC} → ${CYAN}Activity Log Viewer${NC}"
echo -e "  ${BOLD}Terminal 2${NC} → ${GREEN}Developer Alice${NC}"
echo -e "  ${BOLD}Terminal 3${NC} → ${GREEN}Developer Bob${NC}"
echo -e "  ${BOLD}Terminal 4${NC} → ${BLUE}Watcher Alice${NC}"
echo -e "  ${BOLD}Terminal 5${NC} → ${BLUE}Watcher Bob${NC}"
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 1: Developer Intent Declaration${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Alice and Bob are about to declare their intent to modify auth.py"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Watch for developer entries appearing in real-time"
echo -e "    • First entry: alice with lock_state=ACQUIRED"
echo -e ""
echo -e "  ${BOLD}Terminal 2 (Developer Alice):${NC}"
echo -e "    • ⏱️  [T+0s] Declaring intent..."
echo -e "    • ✅ Intent logged"
echo ""
echo -e "  ${BOLD}Terminal 3 (Developer Bob):${NC}"
echo -e "    • Waiting (will start after Alice)"
echo ""
echo -e "  ${BOLD}Terminal 4 & 5 (Watchers):${NC}"
echo -e "    • Monitoring for conflicts"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to start the demo...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 2: Bob Declares Intent (Lock Applied)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Bob declares intent on same file (auth.py) → Conflict detected!"
echo -e "   Lock applies automatically to prevent wasted code generation"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Watch for Bob's entry appearing"
echo -e "    • Bob's lock_state: ${RED}WAITING${NC}"
echo -e "    • queue_position: ${RED}1${NC} (first in queue, waiting for alice)"
echo ""
echo -e "  ${BOLD}Terminal 3 (Developer Bob):${NC}"
echo -e "    • ⏱️  [T+1s] Declaring intent..."
echo -e "    • ⏱️  [T+2s] Checking for conflicts..."
echo -e "    • ${RED}⚠️  Risk Level: MEDIUM${NC}"
echo -e "    • ${RED}🔒 Queue Position: 1${NC}"
echo -e "    • ${RED}⏳ Waiting for: alice${NC}"
echo ""
echo -e "  ${BOLD}Terminal 5 (Watcher Bob):${NC}"
echo -e "    • ⏱️  [T+1s] Initial check..."
echo -e "    • Risk = ${RED}MEDIUM${NC} | Queue Position: ${RED}0${NC}"
echo ""
echo -e "${CYAN}This is the key Neo feature:${NC}"
echo -e "  • Bob doesn't start generating code"
echo -e "  • Bob waits for Alice to finish"
echo -e "  • This prevents merge conflicts and wasted tokens"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 3: Alice Checks Conflicts (No Conflicts for Lock Holder)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Alice checks for conflicts on her file → Sees NO conflicts"
echo -e "   Lock holder doesn't see waiting developers as conflicts"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 2 (Developer Alice):${NC}"
echo -e "    • ⏱️  [T+1s] Checking for conflicts..."
echo -e "    • ✅ Risk Level: ${GREEN}LOW${NC}"
echo -e "    • Message: 'No conflicting work detected'"
echo ""
echo -e "  ${BOLD}Terminal 4 (Watcher Alice):${NC}"
echo -e "    • ⏱️  [T+2s] Risk = ${GREEN}LOW${NC} ✅ (No conflicts)"
echo -e "    • Continues monitoring at T+4s, T+6s, T+8s"
echo ""
echo -e "${CYAN}Key insight:${NC}"
echo -e "  • Alice generates code safely"
echo -e "  • Bob's WAITING state doesn't count as a conflict for Alice"
echo -e "  • Only actual overlapping work = conflict"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 4: Alice Generates & Publishes (Lock Released)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Alice generates code and publishes changes"
echo -e "   Lock automatically released → Bob promoted to next in queue"
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 2 (Developer Alice):${NC}"
echo -e "    • ⏱️  [T+3s] Generating code..."
echo -e "    •    ✏️  Generated: password_hash() function"
echo -e "    •    ✏️  Generated: verify_hash() function"
echo -e "    •    ✏️  Generated: bcrypt integration"
echo -e ""
echo -e "    • ⏱️  [T+4s] Publishing changes..."
echo -e "    • ${GREEN}✅ Code published to repository${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Alice's entry updated with changes published"
echo -e "    • Lock still showing transitions happening"
echo ""
echo -e "${CYAN}What just happened:${NC}"
echo -e "  • Alice's lock released automatically"
echo -e "  • Bob promoted from WAITING → ACQUIRED"
echo -e "  • Bob can now proceed with fresh context"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to continue...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 5: Bob Gets Fresh Context & Starts Generating${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Bob detects Alice's work, gets fresh context, generates based on it"
echo -e "   No stale code, no re-reading entire files (saves 460+ tokens)"
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
echo -e "    •    ✏️  Generated: Token validation middleware"
echo -e "    •    ✏️  Generated: Refresh token logic"
echo ""
echo -e "  ${BOLD}Terminal 5 (Watcher Bob):${NC}"
echo -e "    • ⏱️  [T+5s] Retry after Alice completes..."
echo -e "    • Risk = ${GREEN}LOW${NC} ✅"
echo -e "    • ${GREEN}Lock released - Bob can proceed!${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Bob's entry now shows: lock_state=${GREEN}ACQUIRED${NC}"
echo -e "    • queue_position: ${GREEN}null${NC} (no longer waiting)"
echo ""
echo -e "${CYAN}Token efficiency in action:${NC}"
echo -e "  • Without Neo: Bob re-reads entire file = 500 tokens wasted"
echo -e "  • With Neo: Bob gets delta from activity log = 7 tokens"
echo -e "  • Savings: 493 tokens per developer"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to see completion...${NC}"
read -r

clear
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}STEP 6: Bob Publishes (Workflow Complete)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📍 ${BOLD}What's happening:${NC}"
echo -e "   Bob publishes his changes. Both developers done. Zero conflicts."
echo ""
echo -e "👁️  ${BOLD}What to look for:${NC}"
echo ""
echo -e "  ${BOLD}Terminal 3 (Developer Bob):${NC}"
echo -e "    • ⏱️  [T+7s] Publishing changes..."
echo -e "    • ${GREEN}✅ Code published to repository${NC}"
echo -e "    • ${YELLOW}Bob workflow complete!${NC}"
echo ""
echo -e "  ${BOLD}Terminal 1 (Activity Log):${NC}"
echo -e "    • Complete history of both developers"
echo -e "    • All lock states captured"
echo -e "    • Queue progression visible"
echo ""
echo -e "${CYAN}Demo Summary:${NC}"
echo -e "  ✅ 0 merge conflicts (prevented at semantic layer)"
echo -e "  ✅ 0 manual resolution needed"
echo -e "  ✅ ~1,000 tokens saved (vs 1,000s wasted on context re-reads)"
echo -e "  ✅ Both developers' context fresh"
echo -e "  ✅ Automatic coordination (no manual queue management)"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}This is Neo: Semantic Multi-Developer Coordination${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Try 3-developer demo: ${BOLD}./launch_guided_3dev_demo.sh${NC}"
echo -e "  2. Run manual tests: ${BOLD}pytest tests/test_phase2_waiting_agent_fix.py${NC}"
echo -e "  3. Check activity log: ${BOLD}cat .devsync/activity-log.json | python -m json.tool${NC}"
echo ""
echo -e "${YELLOW}Press ${BOLD}Enter${YELLOW} to close this guide...${NC}"
read -r

echo ""
echo -e "${GREEN}✅ Guide complete!${NC}"
echo -e "${YELLOW}The Terminal windows will remain open. You can close them individually.${NC}"
echo ""
