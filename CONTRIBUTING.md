# Contributing to Ma'at

Thank you for your interest in contributing to Ma'at! This document provides guidelines and instructions for contributing to the project.

## 🎯 Vision

Ma'at is a coordination framework for distributed AI agents and developers working on shared codebases. We're building a system that prevents merge conflicts before code is written by enabling agents to coordinate their work automatically.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Git
- Familiarity with async/await patterns
- Basic understanding of state machines

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/codeNinja.git
cd codeNinja

# Create a virtual environment (optional)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install pytest pytest-asyncio
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_state_machine.py
```

### Running Examples

```bash
# Run CLI simulation
python3 cli_simulation.py

# Open interactive dashboard
open ui_dashboard.html  # or use your browser
```

## 📝 Development Workflow

### 1. Pick an Issue

See [ROADMAP.md](ROADMAP.md) for priority areas:

**Good for First-Time Contributors:**
- Writing tests for edge cases
- Improving documentation
- Adding examples
- Fixing bugs in tooling

**Experienced Backend Developers:**
- Implementing coordination service
- Adding database backends
- Performance optimizations

**Frontend/Full-Stack Developers:**
- Building monitoring dashboard
- Creating IDE plugins
- Notification integrations

**DevOps/Platform Engineers:**
- Kubernetes deployment configs
- Terraform modules
- CI/CD pipeline integrations

### 2. Create a Branch

```bash
# Create a feature branch from main
git checkout -b feature/your-feature-name

# Or from an issue
git checkout -b fix/issue-123-short-description
```

**Branch naming conventions:**
- `feature/` — New capability
- `fix/` — Bug fix
- `docs/` — Documentation
- `test/` — Tests
- `refactor/` — Code quality improvement

### 3. Make Your Changes

**Code Style:**
- Follow PEP 8 for Python
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions focused and testable

**Example:**

```python
async def check_conflicts(
    self,
    agent_id: str,
    file_path: str,
    region: str
) -> Dict[str, Any]:
    """
    Check for conflicts on a file region.
    
    Args:
        agent_id: Unique identifier for the agent
        file_path: Path to the file being accessed
        region: Specific region (e.g., "lines 40-80" or "function_name")
    
    Returns:
        Dictionary with risk_score, conflicting_agents, and recommendations
    
    Raises:
        ValueError: If inputs are invalid
    """
    # Implementation
    pass
```

### 4. Write/Update Tests

Every feature needs tests:

```bash
# Create test file for your feature
touch tests/test_my_feature.py

# Add test cases
pytest tests/test_my_feature.py -v
```

Example test structure:

```python
import pytest
from module import function_to_test

@pytest.mark.asyncio
async def test_happy_path():
    result = await function_to_test(valid_input)
    assert result == expected_output

@pytest.mark.asyncio
async def test_error_handling():
    with pytest.raises(ValueError):
        await function_to_test(invalid_input)
```

### 5. Commit Your Changes

Write clear, descriptive commit messages:

```bash
# Good commit message
git commit -m "feat: Add WebSocket event subscription for lock_removed events

- Implement async event listener pattern
- Add retry logic with exponential backoff
- Test with mock WebSocket server
- Add timeout after 1 hour of waiting

Fixes #42"

# Avoid vague messages
# git commit -m "fix stuff"  ❌
```

**Commit message format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `test:` — Tests
- `refactor:` — Code quality
- `perf:` — Performance

### 6. Open a Pull Request

```bash
# Push your branch
git push -u origin feature/your-feature-name

# Open PR on GitHub
# Title: Short description of change
# Description: What, why, and how
```

**PR Template (use this as a guide):**

```markdown
## Description
Brief explanation of the change.

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123

## Changes
- What specifically changed
- Key implementation details
- Decisions made

## Testing
- [ ] Tests pass locally
- [ ] Added/updated tests
- [ ] Manual testing completed

## Documentation
- [ ] Updated README if needed
- [ ] Added docstrings
- [ ] Updated ROADMAP if applicable
```

### 7. Code Review

Expect feedback on:
- **Correctness** — Does it work as intended?
- **Quality** — Is it maintainable and well-documented?
- **Testing** — Is it adequately tested?
- **Performance** — Are there any concerns?
- **Security** — Any vulnerabilities?

Respond to feedback and push updates:

```bash
# Make requested changes
git add .
git commit -m "Address review feedback: clarify docstring"

# Push (force-push only if asked)
git push
```

## 📚 Documentation Guidelines

### For Code
- Docstrings on all public functions/classes
- Type hints on function signatures
- Example usage in docstrings for complex functions
- Comments only for "why", not "what"

### For Markdown
- Clear headings with `#`, `##`, `###`
- Code examples with syntax highlighting
- Links to related docs
- Table of contents for long docs

### For Diagrams
- Use tools that generate text/SVG (Mermaid, PlantUML, SVG)
- Avoid raster images when possible
- Include alt text

## 🧪 Testing Standards

**Minimum coverage:** 80% for core modules
- Unit tests for isolated functions
- Integration tests for workflows
- Async tests for event-driven code

```bash
# Check coverage
pytest --cov=coordination_state_machine tests/
```

## 🔒 Security

### Before Submitting
- [ ] No secrets/credentials in code
- [ ] No hardcoded API keys
- [ ] No `.env` files committed
- [ ] Dependencies are up-to-date and secure

### Reporting Security Issues
Please report security vulnerabilities privately to the maintainers rather than opening a public issue.

## 📋 Review Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guide
- [ ] Added/updated docstrings
- [ ] Wrote tests for new features
- [ ] Tests pass locally
- [ ] No security issues introduced
- [ ] Updated relevant documentation
- [ ] Commit messages are clear
- [ ] No merge conflicts with main branch
- [ ] Changes are focused (one feature per PR)

## 🎓 Learning Resources

### Understanding the Project
- [OVERVIEW.md](OVERVIEW.md) — System architecture
- [ROADMAP.md](ROADMAP.md) — Future direction
- [docs/INTEGRATION_ARCHITECTURE.md](docs/INTEGRATION_ARCHITECTURE.md) — Deployment patterns

### Framework Integration Guides
- [docs/ENTERPRISE_SCALING_CLAUDE.md](docs/ENTERPRISE_SCALING_CLAUDE.md) — Claude SDK
- [docs/ENTERPRISE_SCALING_OPENAI.md](docs/ENTERPRISE_SCALING_OPENAI.md) — OpenAI API
- [docs/ENTERPRISE_SCALING_DEVIN.md](docs/ENTERPRISE_SCALING_DEVIN.md) — Devin agent
- [docs/ENTERPRISE_SCALING_CODEX.md](docs/ENTERPRISE_SCALING_CODEX.md) — GitHub Copilot

## ❓ Questions?

- **Technical questions:** Open a GitHub discussion
- **Bug reports:** Open an issue with a minimal reproduction
- **Feature requests:** Open an issue with use case and examples
- **Security issues:** Email maintainers privately

## 📜 Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## 🙏 Thank You

Thank you for contributing to Ma'at. Every contribution—whether code, docs, bug reports, or feature ideas—helps build better coordination for distributed teams and AI agents.

---

**Happy contributing! 🚀**
