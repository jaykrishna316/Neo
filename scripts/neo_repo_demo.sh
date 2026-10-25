#!/usr/bin/env bash
# Single-developer Neo demo for a repo where Neo is installed (.neo/).
#
#   .neo/scripts/neo_repo_demo.sh setup     add neo_demo/ with a breaking change left open
#                                         by a previous developer
#   .neo/scripts/neo_repo_demo.sh teammate  a teammate adds a function to pricing.py after
#                                         you have read it (run after you fix checkout.py)
#   .neo/scripts/neo_repo_demo.sh cleanup   delete neo_demo/ and the demo's Neo state
#
# Run from the repo root, where Neo is installed. The copy in .neo/ is the one installed
# by scripts/install_neo.sh.
set -euo pipefail

case $# in
    1) REPO="$(pwd)"; MODE="$1" ;;
    2) REPO="$(cd "$1" && pwd)"; MODE="$2" ;;
    *)
        echo "usage: $0 setup|teammate|cleanup" >&2
        exit 2
        ;;
esac
HOOK="$REPO/.neo/scripts/neo_hook.py"
DEMO="neo_demo"

if [ ! -f "$HOOK" ]; then
    echo "Neo is not installed in $REPO. Run install_neo.sh there first." >&2
    exit 1
fi
cd "$REPO"

hook() {
    # One hook call as a named developer, the way Claude Code makes it.
    local developer="$1" mode="$2" file="$3"
    echo "{\"tool_input\": {\"file_path\": \"$file\"}}" | NEO_DEVELOPER="$developer" python3 "$HOOK" "$mode" > /dev/null
}

stop_task() {
    echo "{}" | NEO_DEVELOPER="$1" python3 "$HOOK" stop > /dev/null
}

case "$MODE" in
    setup)
        mkdir -p "$DEMO"
        cat > "$DEMO/pricing.py" <<'PY'
def price(item):
    return item["cost"] * 1.2
PY
        cat > "$DEMO/checkout.py" <<'PY'
from pricing import price


def total(items):
    return sum(price(item) for item in items)
PY
        # The previous developer adds a tax_rate argument to price() and stops
        # before updating checkout.py.
        hook previous read "$DEMO/pricing.py"
        hook previous pre "$DEMO/pricing.py"
        cat > "$DEMO/pricing.py" <<'PY'
def price(item, tax_rate):
    return item["cost"] * (1 + tax_rate)
PY
        hook previous post "$DEMO/pricing.py"
        stop_task previous
        echo "Setup done. The previous developer left price() changed, and checkout.py still calls it with one argument."
        ;;
    teammate)
        hook teammate read "$DEMO/pricing.py"
        hook teammate pre "$DEMO/pricing.py"
        printf '\n\ndef discount(item):\n    return item["cost"] * 0.9\n' >> "$DEMO/pricing.py"
        hook teammate post "$DEMO/pricing.py"
        stop_task teammate
        echo "Teammate added discount() to $DEMO/pricing.py."
        ;;
    cleanup)
        rm -rf "$DEMO"
        rm -f .neo_state/*pricing* .neo_state/*checkout* .neo_state/intent_previous.txt .neo_state/intent_teammate.txt
        if [ -f .neo_state/breakages.json ]; then echo "[]" > .neo_state/breakages.json; fi
        echo "Demo removed from $REPO."
        ;;
    *)
        echo "unknown mode: $MODE" >&2
        exit 2
        ;;
esac
