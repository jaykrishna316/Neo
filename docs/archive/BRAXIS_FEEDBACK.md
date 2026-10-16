# Feedback: Braxis Context Generation for MCP/Custom Tool Projects

## Context
Tested Braxis on Neo (semantic multi-developer coordination engine with MCP server integration). The generation worked but produced generic outputs that missed critical project-specific details.

## What Worked ✅
- Fast execution
- Detected tech stack (Python, pytest)
- Generated valid AI readiness score (77/100)
- Zero-config workflow
- Created multiple context file formats

## Gaps Identified 🔍

### 1. **Missing MCP Server Configuration**
Braxis skipped entirely:
- MCP server definitions (.mcp servers in settings)
- Tool documentation (neo_check_conflicts, neo_log_activity, etc.)
- MCP-specific setup instructions
- IDE integration details

**Impact**: Agents don't understand available tools/APIs

**Suggestion**: Detect MCP servers in project structure and document them in CLAUDE.md and AGENTS.md

---

### 2. **Project Architecture Oversimplified**
Generated: "This is a Python project"
Actual: Semantic coordination engine with phases, state machines, activity logs, risk classifiers

**Impact**: Agents miss domain-specific patterns and conventions

**Suggestion**: 
- Add optional `braxis.config.json` to capture architecture narrative
- Include diagrams or architecture descriptions in generated files
- Support custom sections in CLAUDE.md template

---

### 3. **Missing Workflow/Process Documentation**
Generated files had no mention of:
- Git branch strategy (neo-4.0 is designated feature branch)
- Development workflow (semantic layer conflict detection before Git merge)
- Custom conventions (risk classification levels, activity log format)

**Impact**: Agents don't follow project-specific workflows

**Suggestion**: Auto-detect workflow markers in README/docs and extract into AGENTS.md

---

### 4. **Generic Output for Specialized Projects**
The 4-line CLAUDE.md works for simple projects but fails for:
- Projects with MCP servers
- Projects with custom IDE integrations
- Projects with domain-specific patterns
- Projects that coordinate across multiple agents

**Suggestion**: Add "project profile" detection that escalates detail level based on complexity signals:
- If MCP server present → include MCP section
- If .claude/settings.json present → include IDE setup
- If multiple modules/layers → include architecture overview

---

## Concrete Suggestions

### Short-term (Low effort)
1. **MCP Detection**: Scan for `ide/mcp_*.py` or MCP server configs and document tools
2. **Custom Sections**: Support injecting raw Markdown sections into generated files via `braxis.config.json`
3. **Template Expansion**: Detect project complexity and expand CLAUDE.md template accordingly

### Medium-term
1. **Architecture Narrative**: Ask LLM to infer project purpose/architecture from code patterns
2. **Pattern Recognition**: Detect semantic layers (risk classifiers, state machines, queues) and document them
3. **Workflow Extraction**: Parse docs for workflow keywords and surface in AGENTS.md

### Long-term
1. **Domain Awareness**: Support industry-specific profiles (coordination engines, ML pipelines, multi-agent systems)
2. **Interactive Mode**: Let users augment generated files with custom sections, then preserve on regenerate
3. **Score Breakdown**: Explain which areas drove the 77/100 score and how to improve each

---

## Why This Matters
Projects with:
- Multiple coordinating agents (Claude, Cursor, Copilot, etc.)
- Custom tool integrations (MCP servers, CLIs, APIs)
- Specialized architectures (coordination engines, state machines, etc.)

...need context files that capture their unique patterns, not generic boilerplate.

Braxis is close to solving this at scale. These gaps prevent it from being the standard for AI-native projects.

---

## Test Case
Neo repository: https://github.com/jaykrishna316/Neo
- MCP server: `ide/mcp_neo_server.py`
- Custom config: `CLAUDE.md` (188 lines of project-specific setup)
- Workflow: Semantic coordination before Git merge
- Result: Braxis generated 4-line CLAUDE.md (missed all context)

Fixing these gaps would make Braxis ideal for this class of projects.
