# Git-Activity Log Bridge Setup Guide

**Purpose:** Automatically add required approvers to GitHub PRs based on HIGH conflicts detected in the activity log.

---

## 🎯 Quick Overview

When a developer/agent creates a PR:
1. **GitActivityLogBridge scans** the activity log for HIGH conflicts
2. **Extracts all developers** involved in those conflicts
3. **Finds the PR number** on GitHub for the current branch
4. **Auto-adds those developers** as required reviewers
5. **They see notifications** and must approve before merge to main

---

## 📋 Prerequisites

- Python 3.7+
- `requests` library installed
- GitHub personal access token with PR permissions
- Repository cloned with Git

---

## 🚀 Setup Steps

### 1. Set GitHub Token

```bash
# Generate token: GitHub Settings > Developer settings > Personal access tokens
# Token needs: repo (full), pull_requests (write)

# Set as environment variable (add to ~/.bashrc or ~/.zshrc):
export GITHUB_TOKEN="github_pat_xxxxxxxxxxxx"

# OR set for current session only:
export GITHUB_TOKEN="github_pat_xxxxxxxxxxxx"

# Verify it's set:
echo $GITHUB_TOKEN
```

### 2. Install Git Hooks (Optional)

The bridge can automatically install three git hooks:

```bash
cd /path/to/Neo
python3 .claude/git_activity_log_bridge.py --setup-hooks

# This creates:
# .git/hooks/pre-commit     - Records changes to activity log
# .git/hooks/pre-push       - Enforces merge gate before push to main
# .git/hooks/post-merge     - Auto-adds approvers to PR
```

### 3. Verify Installation

```bash
ls -la .git/hooks/
# Should show: pre-commit, pre-push, post-merge (with execute permissions)

chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
chmod +x .git/hooks/post-merge
```

---

## 💡 Usage Examples

### Example 1: Auto-Add Approvers When PR Created

```python
from git_activity_log_bridge import GitActivityLogBridge

bridge = GitActivityLogBridge(repo_path=".")

# When a PR is created on feature/my-branch
result = bridge.auto_add_approvers_to_mr(head_branch="feature/my-branch")

print(result)
# Output:
# {
#   "success": True,
#   "pr_number": 42,
#   "approvers_added": ["Agent1", "Agent2"],
#   "conflicts": [...]
# }
```

### Example 2: Find Required Approvers Manually

```python
bridge = GitActivityLogBridge()

# Get all developers involved in HIGH conflicts
approvers = bridge.get_required_approvers(
    base_branch="main",
    head_branch="feature/my-branch"
)

print(f"Must approve: {approvers}")
# Output: Must approve: ['Agent1', 'Agent2']
```

### Example 3: Check PR Number for Branch

```bridge = GitActivityLogBridge()

pr_num = bridge.get_pr_number_from_branch("feature/my-branch")
print(f"PR #{pr_num}")
```

---

## 🔧 API Reference

### `GitActivityLogBridge(repo_path=".", github_token=None)`

Initialize bridge. Token defaults to `$GITHUB_TOKEN` environment variable.

### `get_repo_info() -> Dict`
Returns:
```python
{
  "owner": "jaykrishna316",
  "repo": "Neo",
  "origin": "git@github.com:jaykrishna316/Neo.git"
}
```

### `find_high_conflicts_in_pr(base_branch="main", head_branch=None) -> List[Dict]`
Scans activity log for HIGH conflicts. Returns list of conflict records:
```python
{
  "file": "auth.py",
  "function": "validate_user",
  "severity": "HIGH",
  "developers_involved": ["Agent1", "Agent2"],
  "descriptions": ["Refactored validation", "Added email check"],
  "changes_count": 2,
  "downstream_impacts": {...}
}
```

### `get_required_approvers(base_branch="main", head_branch=None) -> List[str]`
Returns list of developer names who must approve.

### `get_pr_number_from_branch(head_branch) -> Optional[int]`
Returns PR number for the given branch, or None if not found.

### `add_required_reviewers_to_pr(pr_number: int, reviewers: List[str]) -> Dict`
Adds reviewers to GitHub PR. Returns:
```python
{
  "success": True,
  "reviewers_added": ["Agent1", "Agent2"],
  "pr_number": 42
}
```

### `auto_add_approvers_to_mr(head_branch=None) -> Dict`
**Main orchestration method** - does everything:
1. Finds HIGH conflicts in branch
2. Extracts required approvers
3. Finds PR number on GitHub
4. Adds reviewers to PR
5. Returns result

### `set_pr_approval_requirement(pr_number: int, required_approvals: int = 1) -> Dict`
Sets branch protection rule (requires admin access).

---

## 🔗 Integration Workflow

### HIGH Conflict Flow (Agent1 + Agent2 editing same function)

```
⏰ Agent1 starts editing auth.py::validate_user()
   Activity Log: 🔴 LOCK ACQUIRED (hard)

⏰ Agent2 tries to edit same function
   Response: ❌ BLOCKED - Agent1 has lock

⏰ Agent1 commits and pushes to feature/agent1-auth
   Activity Log: 🔴 HIGH CONFLICT DETECTED
   Auto-push: ✅ Queued for feature/agent1-auth

⏰ Agent2 commits and pushes to feature/agent2-auth
   Activity Log: 🔴 HIGH CONFLICT DETECTED
   Auto-push: ✅ Queued for feature/agent2-auth

⏰ Agent1 creates PR from feature/agent1-auth to main
   GitHub Hook: Triggered
   GitActivityLogBridge: 
   ├─ Scans activity log for HIGH conflicts ✅ Found
   ├─ Gets required approvers: ["Agent1", "Agent2"] ✅
   ├─ Finds PR #42 ✅
   ├─ Adds reviewers to PR #42 ✅
   └─ Returns success

⏰ GitHub Notification
   Agent1: "Pull request #42 - Awaiting review from Agent2"
   Agent2: "You are requested to review PR #42"

⏰ Agent2 Reviews & Approves
   Activity Log: ✅ Agent2 APPROVED

⏰ Agent1 Reviews & Approves
   Activity Log: ✅ Agent1 APPROVED

⏰ Merge Check
   can_merge_to_main("auth.py", "validate_user")
   → Returns: (True, {"reason": "All developers approved"})

⏰ Merge to main
   ✅ Allowed - all approvals in place
```

---

## 🐛 Troubleshooting

### GitHub Token Not Working

```bash
# Check token is set
echo $GITHUB_TOKEN

# Verify token has correct permissions
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user

# If 401: Token is invalid or expired
# Regenerate at: GitHub Settings > Developer settings > Personal access tokens
```

### PR Number Not Found

```python
bridge = GitActivityLogBridge()

# Debug: Check all open PRs
repo_info = bridge.get_repo_info()
print(f"Repo: {repo_info['owner']}/{repo_info['repo']}")

# Make sure PR exists and is open
# Verify branch name matches exactly
```

### No HIGH Conflicts Found

```python
# Check activity log
bridge = GitActivityLogBridge()
conflicts = bridge.find_high_conflicts_in_pr("main", "feature/my-branch")

if not conflicts:
    print("✅ No HIGH conflicts detected")
else:
    for c in conflicts:
        print(f"🔴 {c['file']}::{c['function']}")
```

### Request Library Missing

```bash
pip install requests

# Or: pip3 install requests
```

---

## 📊 Testing the Integration

### Manual Test

```bash
cd /path/to/Neo

# 1. Create a test branch
git checkout -b test/bridge-demo

# 2. Simulate HIGH conflict in activity log
python3 << 'EOF'
from enhanced_activity_log import EnhancedActivityLogManager

mgr = EnhancedActivityLogManager()

# Log two conflicting changes
mgr.log_change(
    developer="TestAgent1",
    file_path="auth.py",
    function_name="validate_user",
    old_code="def validate(u, p): return check(u, p)",
    new_code="def validate(u, p): return db.check(u, p)",
    feature_branch="feature/test1",
    verbal_description="Refactored validation"
)

mgr.log_change(
    developer="TestAgent2",
    file_path="auth.py",
    function_name="validate_user",
    old_code="def validate(u, p): return check(u, p)",
    new_code="def validate(u, p, e=False): return check(u, p, e)",
    feature_branch="feature/test2",
    verbal_description="Added email validation"
)
EOF

# 3. Check conflicts detected
python3 << 'EOF'
from git_activity_log_bridge import GitActivityLogBridge

bridge = GitActivityLogBridge()
conflicts = bridge.find_high_conflicts_in_pr("main", "test/bridge-demo")

print(f"HIGH conflicts found: {len(conflicts)}")
for c in conflicts:
    print(f"  - {c['file']}::{c['function']}")
    print(f"    Developers: {c['developers_involved']}")

approvers = bridge.get_required_approvers("main", "test/bridge-demo")
print(f"\nRequired approvers: {approvers}")
EOF

# 4. Create a real PR and test auto-add
git add .activity_log/ && git commit -m "Test: Simulate HIGH conflict"
git push origin test/bridge-demo

# (Create PR manually on GitHub)

# 5. Run auto-add approvers
python3 << 'EOF'
import os
from git_activity_log_bridge import GitActivityLogBridge

os.environ["GITHUB_TOKEN"] = input("Enter GitHub token: ")

bridge = GitActivityLogBridge()
result = bridge.auto_add_approvers_to_mr("test/bridge-demo")

print(result)
EOF
```

---

## ✅ Verification Checklist

- [ ] GITHUB_TOKEN environment variable is set
- [ ] `requests` library installed (`pip list | grep requests`)
- [ ] Git hooks installed (`ls -la .git/hooks/`)
- [ ] Activity log directory exists (`.activity_log/`)
- [ ] Can access GitHub API (`curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user`)
- [ ] Test branch with HIGH conflict created
- [ ] Test PR created
- [ ] Approvers auto-added to test PR
- [ ] Developers see notifications

---

## 🎯 Next Steps

1. **Configure GITHUB_TOKEN** in your environment
2. **Test with a demo PR** using the manual test above
3. **Install git hooks** if auto-triggering desired
4. **Monitor activity log** for conflicts
5. **Verify approvers** are auto-added to PRs

---

## 📞 Support

Refer to:
- `git_activity_log_bridge.py` - Full implementation
- `enhanced_activity_log.py` - Activity log manager
- `FULL_SYSTEM_README.md` - Complete system overview
- `demo_full_activity_log.py` - Example scenarios
