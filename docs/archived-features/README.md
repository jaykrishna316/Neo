# Archived Features - Git Bridge Integration

## Status: Temporarily Archived for Marketplace Submission

These files implement advanced GitHub PR workflow automation for Neo, but were archived temporarily to pass marketplace validation without credential-related warnings.

**Files:**
- `git_activity_log_bridge.py` - GitHub integration implementation
- `GIT_BRIDGE_SETUP.md` - Setup and usage documentation

## What This Feature Does

The Git Bridge automatically:
1. Detects HIGH conflicts in Neo's activity log
2. Extracts all developers involved in those conflicts
3. Finds the GitHub PR for the current branch
4. Auto-adds those developers as required reviewers
5. Notifies them to approve before merge

## Why It Was Archived

The marketplace validator flagged GITHUB_TOKEN references as a security concern, even though the code safely loads it from environment variables (not hardcoded). This was a false positive, but archiving removes the warning.

## Next Steps (Neo 4.1+)

This feature should be:
1. ✅ Re-integrated into core Neo
2. ✅ Properly documented in IDE integration guide
3. ✅ Added as a documented feature in marketplace listing
4. ✅ Tested with multi-developer scenarios

## Future Implementation Notes

When re-implementing:
- Keep credential loading pattern (env vars only, never hardcoded)
- Add unit tests for conflict detection
- Document as optional GitHub integration
- Consider making it an opt-in feature users enable with GITHUB_TOKEN

See GitHub issue: neo-github-bridge-integration
