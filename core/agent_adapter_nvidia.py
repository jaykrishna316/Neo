#!/usr/bin/env python3
"""NVIDIA NIM Agent Adapter for Neo Coordination.

This adapter enables NVIDIA NIM agents to coordinate with Neo, ensuring
zero merge conflicts when multiple NIM-powered agents generate code
simultaneously.

The adapter wraps NVIDIA NIM API calls with Neo's conflict detection,
so agents check for conflicts BEFORE calling NIM for code generation.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from core.agent_adapter import AgentAdapter, AgentInfo

logger = logging.getLogger("Neo-NVIDIA-Adapter")


@dataclass
class NVIDIANIMConfig:
    """Configuration for NVIDIA NIM integration."""

    nim_api_endpoint: str = "http://localhost:8000"  # Default local NIM endpoint
    nim_api_key: Optional[str] = None
    model: str = "nemotron-4-340b-instruct"  # Default NVIDIA model
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9


class NVIDIAAdapter(AgentAdapter):
    """NVIDIA NIM adapter for Neo coordination.

    Enables NVIDIA NIM agents to:
    1. Register with Neo
    2. Check for conflicts before code generation
    3. Call NVIDIA NIM API for code generation
    4. Log completion with metadata
    5. Receive fresh context from previous agents

    This prevents merge conflicts by coordinating semantic intent
    before expensive model API calls.
    """

    def __init__(self, config: Optional[NVIDIANIMConfig] = None):
        """Initialize NVIDIA NIM adapter.

        Args:
            config: NVIDIANIMConfig instance, or None to use environment defaults
        """
        self.config = config or self._load_config_from_env()
        self.agent_registry: Dict[str, AgentInfo] = {}
        self._validate_config()

    def _load_config_from_env(self) -> NVIDIANIMConfig:
        """Load configuration from environment variables."""
        return NVIDIANIMConfig(
            nim_api_endpoint=os.getenv(
                "NVIDIA_NIM_ENDPOINT",
                "http://localhost:8000"
            ),
            nim_api_key=os.getenv("NVIDIA_NIM_API_KEY"),
            model=os.getenv("NVIDIA_NIM_MODEL", "nemotron-4-340b-instruct"),
            max_tokens=int(os.getenv("NVIDIA_NIM_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("NVIDIA_NIM_TEMPERATURE", "0.7")),
            top_p=float(os.getenv("NVIDIA_NIM_TOP_P", "0.9")),
        )

    def _validate_config(self):
        """Validate NIM configuration."""
        if not self.config.nim_api_endpoint:
            logger.warning(
                "NVIDIA_NIM_ENDPOINT not set, defaulting to localhost:8000. "
                "Set NVIDIA_NIM_ENDPOINT environment variable for remote endpoints."
            )
        logger.info(
            f"NVIDIA Adapter initialized: endpoint={self.config.nim_api_endpoint}, "
            f"model={self.config.model}"
        )

    def check_conflicts(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check for conflicts BEFORE calling NVIDIA NIM API.

        This is the critical integration point: by checking Neo's activity log
        BEFORE generating code, we prevent wasted API calls on conflicting work.

        Args:
            agent_id: NVIDIA agent identifier
            file_path: File to be modified
            intent: Description of intended code generation
            region: Optional code region (function, class, etc.)

        Returns:
            Dict with risk_level, message, should_block, lock_holder, queue_position
        """
        from core.pre_gen_check import check_for_conflicts

        logger.info(f"NVIDIA agent {agent_id} checking conflicts for {file_path}")

        risk_level, message, lock_info = check_for_conflicts(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
        )

        result = {
            "risk_level": risk_level.value if hasattr(risk_level, "value") else str(risk_level),
            "message": message,
            "should_block": str(risk_level).upper() == "HIGH",
            "lock_holder": lock_info.get("lock_holder") if lock_info else None,
            "queue_position": lock_info.get("queue_position") if lock_info else None,
        }

        logger.info(f"Conflict check result: {result['risk_level']} - {message}")
        return result

    def declare_intent(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Declare intent to work on a file.

        Logs the intent to Neo's activity log and acquires lock if available.

        Args:
            agent_id: NVIDIA agent identifier
            file_path: File to modify
            intent: Description of code generation intent
            region: Optional code region
            dependencies: Optional list of dependent files

        Returns:
            Dict with success, lock_state, message
        """
        from core.activity_log import log_activity

        logger.info(f"NVIDIA agent {agent_id} declaring intent on {file_path}")

        try:
            entry = log_activity(
                developer_id=agent_id,
                file_path=file_path,
                intent=intent,
                region=region,
                intent_category="nvidia_generation",
                agent_metadata={
                    "dependencies": dependencies or [],
                    "agent_type": "nvidia_nim",
                    "model": self.config.model,
                },
            )

            result = {
                "success": True,
                "lock_state": entry.get("lock_state", "UNKNOWN"),
                "message": f"Intent declared for {agent_id} on {file_path}",
            }
            logger.info(f"Intent declared: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to declare intent: {str(e)}")
            return {"success": False, "message": f"Failed to declare intent: {str(e)}"}

    def call_nvidia_nim(
        self,
        agent_id: str,
        prompt: str,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call NVIDIA NIM API for code generation.

        This method handles the actual API call to NVIDIA's inference endpoint.
        In production, would use the official NVIDIA SDK.

        Args:
            agent_id: Agent making the request
            prompt: Prompt for code generation
            file_path: Optional file path for context

        Returns:
            Dict with generated_code, tokens_used, model, etc.
        """
        try:
            # Import requests lazily to avoid hard dependency
            import requests

            logger.info(f"NVIDIA agent {agent_id} calling NIM API for code generation")

            # Prepare NIM API request
            headers = {
                "Content-Type": "application/json",
            }
            if self.config.nim_api_key:
                headers["Authorization"] = f"Bearer {self.config.nim_api_key}"

            payload = {
                "model": self.config.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert code generation assistant. Generate clean, well-documented, production-ready code."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "max_tokens": self.config.max_tokens,
            }

            # Call NIM endpoint
            response = requests.post(
                f"{self.config.nim_api_endpoint}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()

            result = response.json()
            generated_code = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = result.get("usage", {}).get("total_tokens", 0)

            logger.info(
                f"NIM generation complete: {tokens_used} tokens, "
                f"{len(generated_code)} chars"
            )

            return {
                "success": True,
                "generated_code": generated_code,
                "tokens_used": tokens_used,
                "model": self.config.model,
                "prompt": prompt,
                "file_path": file_path,
            }

        except ImportError:
            logger.error("requests library not installed. Install with: pip install requests")
            return {
                "success": False,
                "error": "requests library required for NIM API calls",
                "hint": "Install with: pip install requests"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"NIM API call failed: {str(e)}")
            return {
                "success": False,
                "error": f"NIM API error: {str(e)}",
                "endpoint": self.config.nim_api_endpoint,
            }

    def log_completion(
        self,
        agent_id: str,
        file_path: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Log work completion with NIM generation metadata.

        Args:
            agent_id: Agent identifier
            file_path: File modified
            metadata: Completion metadata (lines_added, tokens_used, etc.)

        Returns:
            Dict with success, message
        """
        from core.activity_log import log_activity

        logger.info(f"NVIDIA agent {agent_id} logging completion on {file_path}")

        try:
            # Enhance metadata with NIM specifics
            enhanced_metadata = {
                "status": "completed",
                "agent_type": "nvidia_nim",
                "model": self.config.model,
                **metadata
            }

            entry = log_activity(
                developer_id=agent_id,
                file_path=file_path,
                intent=f"COMPLETED: {metadata.get('summary', 'Code generation completed')}",
                agent_metadata=enhanced_metadata,
            )

            logger.info(f"Completion logged with metadata: {enhanced_metadata}")
            return {"success": True, "message": "Work completion logged"}

        except Exception as e:
            logger.error(f"Failed to log completion: {str(e)}")
            return {"success": False, "message": f"Failed to log completion: {str(e)}"}

    def register_agent(self, agent_info: AgentInfo) -> Dict[str, Any]:
        """Register a NVIDIA NIM agent with Neo.

        Args:
            agent_info: AgentInfo instance with agent metadata

        Returns:
            Dict with success, agent_id, message
        """
        agent_info.registered_at = time.time()
        agent_info.status = "idle"
        self.agent_registry[agent_info.agent_id] = agent_info

        logger.info(
            f"NVIDIA agent registered: {agent_info.agent_id} "
            f"(type: {agent_info.agent_type}, model: {self.config.model})"
        )

        return {
            "success": True,
            "agent_id": agent_info.agent_id,
            "message": f"Agent {agent_info.agent_id} registered as {agent_info.agent_type} "
                      f"with model {self.config.model}",
        }

    def get_fresh_context(
        self,
        agent_id: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """Get fresh context after lock is released.

        When a NVIDIA agent's lock is released, the next agent can request
        fresh context from the previous agent's work, including:
        - Previous agent ID
        - Changes summary
        - Token savings via delta refresh (C2)
        - Next steps

        Args:
            agent_id: Requesting agent
            file_path: File to get context for

        Returns:
            Dict with previous_agent, changes, summary, next_steps, token_savings
        """
        from core.activity_log import read_log
        from core.delta_refresh import DeltaGenerator

        logger.info(f"NVIDIA agent {agent_id} requesting fresh context for {file_path}")

        try:
            entries = read_log()

            # Find most recent completed entry for this file
            previous_entry = None
            for entry in reversed(entries):
                if entry.get("file_path") == file_path and entry.get(
                    "agent_metadata", {}
                ).get("status") == "completed":
                    previous_entry = entry
                    break

            if not previous_entry:
                logger.info(f"No previous work found for {file_path}")
                return {
                    "previous_agent": None,
                    "changes": {},
                    "summary": "No previous work",
                    "next_steps": [],
                    "token_savings": 0,
                }

            # Calculate token savings via delta refresh (C2)
            tokens_saved = 0
            full_file_tokens = previous_entry.get("agent_metadata", {}).get("tokens_used", 500)
            delta_tokens = previous_entry.get("agent_metadata", {}).get("delta_tokens", 40)
            if full_file_tokens > 0:
                tokens_saved = full_file_tokens - delta_tokens

            result = {
                "previous_agent": previous_entry.get("developer_id"),
                "changes": previous_entry.get("agent_metadata", {}),
                "summary": previous_entry.get("intent", "").replace("COMPLETED: ", ""),
                "next_steps": previous_entry.get("agent_metadata", {}).get("next_steps", []),
                "token_savings": tokens_saved,
                "delta_available": delta_tokens < (full_file_tokens * 0.5),  # True if >50% savings
            }

            logger.info(
                f"Fresh context provided: previous_agent={result['previous_agent']}, "
                f"token_savings={tokens_saved}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get fresh context: {str(e)}")
            return {
                "previous_agent": None,
                "changes": {},
                "summary": f"Error getting context: {str(e)}",
                "next_steps": [],
                "token_savings": 0,
            }

    def coordinate_with_nim_workflow(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        generation_prompt: str,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete coordination workflow: check → declare → generate → log.

        This is the high-level method that orchestrates the entire flow:
        1. Check for conflicts (Neo semantic layer)
        2. Declare intent and acquire lock
        3. Call NVIDIA NIM API for code generation
        4. Log completion with metadata

        Args:
            agent_id: Agent identifier
            file_path: File to modify
            intent: Intent description
            generation_prompt: Prompt for NVIDIA NIM
            region: Optional code region

        Returns:
            Dict with workflow_status, risk_level, generated_code, etc.
        """
        logger.info(
            f"Starting coordination workflow for {agent_id} on {file_path}"
        )

        # Step 1: Check for conflicts
        conflict_check = self.check_conflicts(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
        )

        if conflict_check["should_block"]:
            logger.warning(f"Workflow blocked: {conflict_check['message']}")
            return {
                "workflow_status": "blocked",
                "risk_level": conflict_check["risk_level"],
                "message": conflict_check["message"],
                "lock_holder": conflict_check["lock_holder"],
                "queue_position": conflict_check["queue_position"],
            }

        # Step 2: Declare intent
        declare_result = self.declare_intent(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
        )

        if not declare_result["success"]:
            logger.error(f"Failed to declare intent: {declare_result['message']}")
            return {
                "workflow_status": "failed",
                "error": declare_result["message"],
            }

        # Step 3: Call NVIDIA NIM API
        nim_result = self.call_nvidia_nim(
            agent_id=agent_id,
            prompt=generation_prompt,
            file_path=file_path,
        )

        if not nim_result.get("success"):
            logger.error(f"NIM API call failed: {nim_result.get('error')}")
            return {
                "workflow_status": "failed",
                "error": nim_result.get("error"),
            }

        # Step 4: Log completion
        completion_metadata = {
            "summary": intent,
            "generated_code": nim_result["generated_code"],
            "tokens_used": nim_result["tokens_used"],
            "model": nim_result["model"],
            "status": "completed",
        }

        log_result = self.log_completion(
            agent_id=agent_id,
            file_path=file_path,
            metadata=completion_metadata,
        )

        if not log_result["success"]:
            logger.error(f"Failed to log completion: {log_result['message']}")
            return {
                "workflow_status": "partial",
                "warning": "Code generated but logging failed",
                "generated_code": nim_result["generated_code"],
                "tokens_used": nim_result["tokens_used"],
            }

        logger.info(f"Workflow completed successfully for {agent_id}")
        return {
            "workflow_status": "success",
            "agent_id": agent_id,
            "file_path": file_path,
            "lock_state": declare_result["lock_state"],
            "generated_code": nim_result["generated_code"],
            "tokens_used": nim_result["tokens_used"],
            "model": nim_result["model"],
            "risk_level": conflict_check["risk_level"],
        }


# Convenience factory function
def create_nvidia_adapter(config: Optional[NVIDIANIMConfig] = None) -> NVIDIAAdapter:
    """Create and return a configured NVIDIA adapter instance.

    Args:
        config: Optional NVIDIANIMConfig; if None, loads from environment

    Returns:
        Initialized NVIDIAAdapter instance
    """
    return NVIDIAAdapter(config)
