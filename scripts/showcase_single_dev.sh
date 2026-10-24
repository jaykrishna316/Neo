#!/usr/bin/env bash
# Sets up the single-developer Neo showcase in this repo.
#
#   scripts/showcase_single_dev.sh setup     reset the files and leave a breaking change
#                                            open, as if a previous developer left it
#   scripts/showcase_single_dev.sh teammate  a teammate adds a small function to the end
#                                            of src/auth.py after you have read it
set -euo pipefail
cd "$(dirname "$0")/.."

hook() {
    # Run one hook call as a named developer, the way Claude Code would.
    local developer="$1" mode="$2" file="$3"
    echo "{\"tool_input\": {\"file_path\": \"$file\"}}" | NEO_DEVELOPER="$developer" python3 scripts/neo_hook.py "$mode" > /dev/null
}

stop_task() {
    # The developer's task ends: their locks are released and their work is marked complete.
    echo "{}" | NEO_DEVELOPER="$1" python3 scripts/neo_hook.py stop > /dev/null
}

case "${1:-}" in
    setup)
        scripts/reset_claude_test.sh
        # The previous developer reads auth.py, changes its signature, and stops there.
        hook previous read src/auth.py
        hook previous pre src/auth.py
        printf "def authenticate(user, password):\n    return password == 'ok'\n" > src/auth.py
        hook previous post src/auth.py
        stop_task previous
        echo "Previous developer's change is in place: authenticate() now takes a password,"
        echo "and payment.py still calls it with one argument."
        ;;
    teammate)
        hook teammate read src/auth.py
        hook teammate pre src/auth.py
        printf "\n\ndef audit_log(user):\n    return None\n" >> src/auth.py
        hook teammate post src/auth.py
        stop_task teammate
        echo "Teammate added audit_log() to the end of src/auth.py."
        ;;
    *)
        echo "usage: $0 setup|teammate" >&2
        exit 2
        ;;
esac
