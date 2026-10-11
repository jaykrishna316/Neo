#!/usr/bin/env python3
"""
Unit tests for NVIDIA NIM Agent Adapter.

Tests the NVIDIAAdapter's core functionality:
- Agent registration
- Conflict detection
- Intent declaration
- Lock state management
- Context retrieval
- Error handling
"""

import unittest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_adapter_nvidia import (
    NVIDIAAdapter,
    NVIDIANIMConfig,
    create_nvidia_adapter,
)
from core.agent_adapter import AgentInfo


class TestNVIDIAAdapterInitialization(unittest.TestCase):
    """Test adapter initialization and configuration."""

    def test_init_with_default_config(self):
        """Test adapter initialization with default config."""
        adapter = NVIDIAAdapter()
        self.assertIsNotNone(adapter.config)
        self.assertEqual(adapter.config.model, "nemotron-4-340b-instruct")
        self.assertEqual(adapter.config.max_tokens, 2048)

    def test_init_with_custom_config(self):
        """Test adapter initialization with custom config."""
        config = NVIDIANIMConfig(
            nim_api_endpoint="http://custom-endpoint:8000",
            model="custom-model",
            max_tokens=4096,
        )
        adapter = NVIDIAAdapter(config)
        self.assertEqual(adapter.config.nim_api_endpoint, "http://custom-endpoint:8000")
        self.assertEqual(adapter.config.model, "custom-model")
        self.assertEqual(adapter.config.max_tokens, 4096)

    def test_load_config_from_env(self):
        """Test loading config from environment variables."""
        with patch.dict(os.environ, {
            "NVIDIA_NIM_ENDPOINT": "http://env-endpoint:8000",
            "NVIDIA_NIM_MODEL": "env-model",
            "NVIDIA_NIM_MAX_TOKENS": "1024",
        }):
            adapter = NVIDIAAdapter()
            self.assertEqual(adapter.config.nim_api_endpoint, "http://env-endpoint:8000")
            self.assertEqual(adapter.config.model, "env-model")
            self.assertEqual(adapter.config.max_tokens, 1024)

    def test_create_adapter_factory(self):
        """Test factory function."""
        adapter = create_nvidia_adapter()
        self.assertIsInstance(adapter, NVIDIAAdapter)


class TestAgentRegistration(unittest.TestCase):
    """Test agent registration functionality."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    def test_register_agent(self):
        """Test registering an agent."""
        agent = AgentInfo(
            agent_id="test-agent",
            agent_type="nvidia_nim",
            capabilities=["code-generation"],
        )
        result = adapter.register_agent(agent)

        self.assertTrue(result["success"])
        self.assertEqual(result["agent_id"], "test-agent")
        self.assertIn("registered", result["message"].lower())

    def test_register_multiple_agents(self):
        """Test registering multiple agents."""
        agents = [
            AgentInfo(agent_id=f"agent-{i}", agent_type="nvidia_nim", capabilities=[])
            for i in range(3)
        ]

        for agent in agents:
            result = self.adapter.register_agent(agent)
            self.assertTrue(result["success"])

        # All should be in registry
        self.assertEqual(len(self.adapter.agent_registry), 3)

    def test_register_sets_timestamps(self):
        """Test that registration sets timestamps."""
        agent = AgentInfo(
            agent_id="test-agent",
            agent_type="nvidia_nim",
            capabilities=[],
        )
        self.assertIsNone(agent.registered_at)
        self.adapter.register_agent(agent)
        self.assertIsNotNone(agent.registered_at)
        self.assertIsNotNone(agent.last_activity)


class TestConflictDetection(unittest.TestCase):
    """Test conflict detection functionality."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    @patch("core.agent_adapter_nvidia.check_for_conflicts")
    def test_check_conflicts_low_risk(self, mock_check):
        """Test low-risk conflict check."""
        mock_check.return_value = ("LOW", "No conflicts", {"lock_holder": None})

        result = self.adapter.check_conflicts(
            agent_id="agent-1",
            file_path="src/module.py",
            intent="Generate code",
        )

        self.assertEqual(result["risk_level"], "LOW")
        self.assertFalse(result["should_block"])
        self.assertIsNone(result["lock_holder"])

    @patch("core.agent_adapter_nvidia.check_for_conflicts")
    def test_check_conflicts_medium_risk(self, mock_check):
        """Test medium-risk conflict check."""
        mock_check.return_value = (
            "MEDIUM",
            "Agent locked",
            {"lock_holder": "agent-1", "queue_position": 0},
        )

        result = self.adapter.check_conflicts(
            agent_id="agent-2",
            file_path="src/module.py",
            intent="Generate tests",
        )

        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertFalse(result["should_block"])
        self.assertEqual(result["lock_holder"], "agent-1")
        self.assertEqual(result["queue_position"], 0)

    @patch("core.agent_adapter_nvidia.check_for_conflicts")
    def test_check_conflicts_high_risk(self, mock_check):
        """Test high-risk conflict check."""
        mock_check.return_value = (
            "HIGH",
            "Critical conflict",
            {"lock_holder": "agent-1", "queue_position": 0},
        )

        result = self.adapter.check_conflicts(
            agent_id="agent-2",
            file_path="src/module.py",
            intent="Generate code",
        )

        self.assertEqual(result["risk_level"], "HIGH")
        self.assertTrue(result["should_block"])


class TestIntentDeclaration(unittest.TestCase):
    """Test intent declaration functionality."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    @patch("core.agent_adapter_nvidia.log_activity")
    def test_declare_intent_success(self, mock_log):
        """Test successful intent declaration."""
        mock_log.return_value = {
            "lock_state": "ACQUIRED",
            "developer_id": "agent-1",
            "file_path": "src/module.py",
        }

        result = self.adapter.declare_intent(
            agent_id="agent-1",
            file_path="src/module.py",
            intent="Generate authentication module",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["lock_state"], "ACQUIRED")

    @patch("core.agent_adapter_nvidia.log_activity")
    def test_declare_intent_waiting_in_queue(self, mock_log):
        """Test intent declaration while waiting in queue."""
        mock_log.return_value = {
            "lock_state": "WAITING",
            "queue_position": 1,
        }

        result = self.adapter.declare_intent(
            agent_id="agent-2",
            file_path="src/module.py",
            intent="Generate tests",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["lock_state"], "WAITING")

    @patch("core.agent_adapter_nvidia.log_activity")
    def test_declare_intent_with_dependencies(self, mock_log):
        """Test declaring intent with dependencies."""
        dependencies = ["src/utils.py", "src/config.py"]
        mock_log.return_value = {"lock_state": "ACQUIRED"}

        result = self.adapter.declare_intent(
            agent_id="agent-1",
            file_path="src/module.py",
            intent="Generate module",
            dependencies=dependencies,
        )

        self.assertTrue(result["success"])
        # Verify dependencies were logged
        call_args = mock_log.call_args
        self.assertIn("dependencies", call_args.kwargs["agent_metadata"])


class TestNIMAPIIntegration(unittest.TestCase):
    """Test NVIDIA NIM API integration."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    @patch("core.agent_adapter_nvidia.requests.post")
    def test_call_nim_success(self, mock_post):
        """Test successful NIM API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "def hello(): pass"}}],
            "usage": {"total_tokens": 250},
        }
        mock_post.return_value = mock_response

        result = self.adapter.call_nvidia_nim(
            agent_id="agent-1",
            prompt="Generate hello function",
            file_path="src/hello.py",
        )

        self.assertTrue(result["success"])
        self.assertIn("def hello():", result["generated_code"])
        self.assertEqual(result["tokens_used"], 250)

    @patch("core.agent_adapter_nvidia.requests.post")
    def test_call_nim_api_error(self, mock_post):
        """Test NIM API error handling."""
        mock_post.side_effect = Exception("Connection failed")

        result = self.adapter.call_nvidia_nim(
            agent_id="agent-1",
            prompt="Generate code",
        )

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @patch("core.agent_adapter_nvidia.requests")
    def test_call_nim_with_auth(self, mock_requests):
        """Test NIM API call with authentication."""
        config = NVIDIANIMConfig(nim_api_key="test-api-key")
        adapter = NVIDIAAdapter(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "code"}}],
            "usage": {"total_tokens": 100},
        }
        mock_requests.post.return_value = mock_response

        adapter.call_nvidia_nim(
            agent_id="agent-1",
            prompt="Generate code",
        )

        # Verify auth header was set
        call_args = mock_requests.post.call_args
        headers = call_args.kwargs.get("headers", {})
        self.assertIn("Authorization", headers)
        self.assertIn("Bearer", headers.get("Authorization", ""))


class TestCompletion(unittest.TestCase):
    """Test work completion logging."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    @patch("core.agent_adapter_nvidia.log_activity")
    def test_log_completion(self, mock_log):
        """Test logging work completion."""
        mock_log.return_value = {"lock_state": "RELEASED"}

        metadata = {
            "summary": "Module implemented",
            "lines_added": 100,
            "tokens_used": 500,
        }

        result = self.adapter.log_completion(
            agent_id="agent-1",
            file_path="src/module.py",
            metadata=metadata,
        )

        self.assertTrue(result["success"])
        self.assertIn("logged", result["message"].lower())

    @patch("core.agent_adapter_nvidia.log_activity")
    def test_log_completion_error_handling(self, mock_log):
        """Test error handling in completion logging."""
        mock_log.side_effect = Exception("Log write failed")

        result = self.adapter.log_completion(
            agent_id="agent-1",
            file_path="src/module.py",
            metadata={},
        )

        self.assertFalse(result["success"])


class TestFreshContext(unittest.TestCase):
    """Test fresh context retrieval."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    @patch("core.agent_adapter_nvidia.read_log")
    def test_get_fresh_context_with_previous_work(self, mock_read):
        """Test retrieving fresh context when previous work exists."""
        mock_read.return_value = [
            {
                "developer_id": "agent-1",
                "file_path": "src/module.py",
                "intent": "COMPLETED: Core implementation",
                "agent_metadata": {
                    "status": "completed",
                    "lines_added": 100,
                    "tokens_used": 500,
                    "delta_tokens": 50,
                },
            }
        ]

        result = self.adapter.get_fresh_context(
            agent_id="agent-2",
            file_path="src/module.py",
        )

        self.assertEqual(result["previous_agent"], "agent-1")
        self.assertIn("Core implementation", result["summary"])
        self.assertGreater(result["token_savings"], 0)

    @patch("core.agent_adapter_nvidia.read_log")
    def test_get_fresh_context_no_previous_work(self, mock_read):
        """Test getting context when no previous work exists."""
        mock_read.return_value = []

        result = self.adapter.get_fresh_context(
            agent_id="agent-1",
            file_path="src/module.py",
        )

        self.assertIsNone(result["previous_agent"])
        self.assertEqual(result["token_savings"], 0)


class TestWorkflowOrchestration(unittest.TestCase):
    """Test complete workflow orchestration."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    @patch("core.agent_adapter_nvidia.check_for_conflicts")
    @patch("core.agent_adapter_nvidia.log_activity")
    @patch("core.agent_adapter_nvidia.requests.post")
    def test_complete_workflow_success(self, mock_post, mock_log_activity, mock_check):
        """Test successful complete workflow."""
        # Setup mocks
        mock_check.return_value = ("LOW", "No conflict", {})
        mock_log_activity.return_value = {"lock_state": "ACQUIRED"}

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "def code(): pass"}}],
            "usage": {"total_tokens": 200},
        }
        mock_post.return_value = mock_response

        # Run workflow
        result = self.adapter.coordinate_with_nim_workflow(
            agent_id="test-agent",
            file_path="src/test.py",
            intent="Generate test file",
            generation_prompt="Generate pytest tests",
        )

        # Verify workflow completed
        self.assertEqual(result["workflow_status"], "success")
        self.assertIn("code", result["generated_code"])
        self.assertEqual(result["risk_level"], "LOW")

    @patch("core.agent_adapter_nvidia.check_for_conflicts")
    def test_workflow_blocked_by_conflict(self, mock_check):
        """Test workflow blocked by high-risk conflict."""
        mock_check.return_value = ("HIGH", "High conflict", {"lock_holder": "agent-1"})

        result = self.adapter.coordinate_with_nim_workflow(
            agent_id="agent-2",
            file_path="src/module.py",
            intent="Generate code",
            generation_prompt="...",
        )

        self.assertEqual(result["workflow_status"], "blocked")
        self.assertTrue(result["lock_holder"])


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def setUp(self):
        self.adapter = NVIDIAAdapter()

    def test_missing_requests_library(self):
        """Test handling when requests library is not available."""
        with patch.dict("sys.modules", {"requests": None}):
            result = self.adapter.call_nvidia_nim(
                agent_id="agent-1",
                prompt="test",
            )
            self.assertFalse(result["success"])
            self.assertIn("requests", result.get("error", "").lower())

    @patch("core.agent_adapter_nvidia.log_activity")
    def test_agent_metadata_enhancement(self, mock_log):
        """Test that agent metadata is properly enhanced."""
        mock_log.return_value = {}

        self.adapter.log_completion(
            agent_id="agent-1",
            file_path="src/test.py",
            metadata={"summary": "Tests", "lines_added": 50},
        )

        call_args = mock_log.call_args
        metadata = call_args.kwargs["agent_metadata"]
        self.assertEqual(metadata["agent_type"], "nvidia_nim")
        self.assertIn("model", metadata)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[""], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
