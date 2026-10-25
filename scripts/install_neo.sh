#!/usr/bin/env bash
# Installs Neo's Claude Code hooks into another git repo.
#
#   scripts/install_neo.sh <target-repo>
#
# Copies the hook and its core modules into <target>/.neo/, adds the hook entries
# to <target>/.claude/settings.json, and ignores Neo's state folders in git.
# Running it again refreshes the copy and the settings without duplicating them.
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "usage: $0 <target-repo>" >&2
    exit 2
fi

TARGET="$(cd "$1" 2>/dev/null && pwd)" || { echo "not a directory: $1" >&2; exit 1; }
NEO="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$NEO/scripts/neo_hook.py" ] || [ ! -d "$NEO/core" ]; then
    echo "not a Neo checkout: $NEO" >&2
    exit 1
fi
if ! git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "not a git repo: $TARGET" >&2
    exit 1
fi

# 1. Copy the hook and core modules. Only Neo's own subfolders are replaced.
DEST="$TARGET/.neo"
rm -rf "$DEST/scripts" "$DEST/core"
mkdir -p "$DEST/scripts" "$DEST/core"
cp "$NEO/scripts/neo_hook.py" "$NEO/scripts/neo_update_check.py" "$NEO/scripts/neo_repo_demo.sh" "$DEST/scripts/"
cp "$NEO"/core/*.py "$DEST/core/"
git -C "$NEO" rev-parse HEAD > "$DEST/VERSION" 2>/dev/null || echo "unknown" > "$DEST/VERSION"

# 2. Add the hook entries to .claude/settings.json, keeping any hooks already there.
python3 - "$TARGET/.claude/settings.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(path.read_text()) if path.exists() else {}
hooks = data.setdefault("hooks", {})

NEO_CMD = "python3 .neo/scripts/"
WANTED = {
    "PreToolUse": [("Write|Edit|MultiEdit|Update", f"{NEO_CMD}neo_hook.py pre", 150)],
    "PostToolUse": [("Write|Edit|MultiEdit|Update", f"{NEO_CMD}neo_hook.py post", 20),
                    ("Read", f"{NEO_CMD}neo_hook.py read", 10),
                    ("Bash", f"{NEO_CMD}neo_hook.py bash", 20)],
    "UserPromptSubmit": [(None, f"{NEO_CMD}neo_hook.py prompt", 10)],
    "Stop": [(None, f"{NEO_CMD}neo_hook.py stop", 20)],
    "SessionStart": [(None, f"{NEO_CMD}neo_update_check.py", 10)],
}


def without_neo(groups):
    """Drop Neo's own entries, so a re-run replaces them instead of adding copies."""
    kept = []
    for group in groups:
        inner = [h for h in group.get("hooks", []) if not h.get("command", "").startswith(NEO_CMD)]
        if inner:
            kept.append({**group, "hooks": inner})
    return kept


for event, entries in WANTED.items():
    groups = without_neo(hooks.get(event, []))
    for matcher, command, timeout in entries:
        group = {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
        if matcher:
            group["matcher"] = matcher
        groups.append(group)
    hooks[event] = groups

path.write_text(json.dumps(data, indent=2) + "\n")
PY

# 3. Keep Neo's state out of git.
GITIGNORE="$TARGET/.gitignore"
touch "$GITIGNORE"
if [ -s "$GITIGNORE" ] && [ "$(tail -c1 "$GITIGNORE" | wc -l)" -eq 0 ]; then
    echo >> "$GITIGNORE"
fi
for entry in ".neo_state/" ".devsync/"; do
    grep -qxF "$entry" "$GITIGNORE" || echo "$entry" >> "$GITIGNORE"
done

echo "Neo hooks installed in $TARGET (Neo $(cut -c1-7 "$DEST/VERSION"))."
echo
echo "Next:"
echo "  1. Review: git -C \"$TARGET\" status"
echo "  2. Commit .neo/, .claude/settings.json and .gitignore so teammates get the hooks."
echo "  3. Each developer sets a name before starting Claude Code:"
echo "       NEO_DEVELOPER=<name> claude"
