"""
IDE-specific adapters for Neo MCP Conflict Notifications

Each adapter translates Neo conflict notifications into IDE-specific UI/warnings:
- claude_code_adapter: Claude Code IDE integration
- devin_adapter: Devin IDE integration
- openai_adapter: OpenAI/Cursor IDE integration
- nvidia_adapter: NVIDIA NIM integration for code generation coordination
"""

from core.agent_adapter_nvidia import NVIDIAAdapter, NVIDIANIMConfig

__all__ = ["NVIDIAAdapter", "NVIDIANIMConfig"]
