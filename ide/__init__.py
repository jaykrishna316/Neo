# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Jayakrishna Ichapurapu
# module-id: 12d07a5e-e3ca1162
"""Claude Code IDE Integration for Neo Conflict Detection.

Provides:
- Pre-generation conflict checking
- MCP server for IDE integration
- Automatic workflow integration
"""

from .claude_code_integration import NeoIDEHook, NeoMCPServer, create_ide_hook

__all__ = [
    "NeoIDEHook",
    "NeoMCPServer",
    "create_ide_hook",
]
