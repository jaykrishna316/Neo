"""
Lean Agent Implementations for Neo MVP Validation
- LocalAgent: Ollama (free, local)
- GroqAgent: Groq free tier API
- SonnetAgent: Claude Sonnet (throttled, minimal cost)
"""

import os
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
import requests
import json


@dataclass
class AgentResponse:
    agent_id: str
    model: str
    response: str
    tokens_used: int
    latency_ms: float
    cost_usd: float


class LocalAgent:
    """Ollama local model - free, unlimited"""

    def __init__(self, model: str = "mistral", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.agent_id = f"local-{model}"

    def check_conflict(self, scenario: Dict[str, Any]) -> AgentResponse:
        """Analyze conflict risk using local model"""
        start = time.time()

        prompt = f"""Analyze this code coordination scenario and predict conflict risk.

File: {scenario['file']}
Agent A: {scenario['intent_a']}
Agent B: {scenario['intent_b']}
Overlap: {scenario['overlap_region']}

Respond with ONLY: CONFLICT or NO_CONFLICT"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            latency_ms = (time.time() - start) * 1000
            tokens_used = len(result.get("response", "").split())

            return AgentResponse(
                agent_id=self.agent_id,
                model=self.model,
                response=result.get("response", "").strip(),
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                cost_usd=0.0  # Free
            )
        except Exception as e:
            print(f"LocalAgent error: {e}")
            return AgentResponse(
                agent_id=self.agent_id,
                model=self.model,
                response=f"ERROR: {str(e)}",
                tokens_used=0,
                latency_ms=(time.time() - start) * 1000,
                cost_usd=0.0
            )


class GroqAgent:
    """Groq free tier API - 30 req/min, free"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = "mixtral-8x7b-32768"  # Free tier model
        self.agent_id = "groq-mixtral"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

        if not self.api_key:
            print("⚠️  GROQ_API_KEY not set. Set with: export GROQ_API_KEY='your_key'")

    def check_conflict(self, scenario: Dict[str, Any]) -> AgentResponse:
        """Analyze conflict risk using Groq"""
        start = time.time()

        prompt = f"""Analyze this code coordination scenario and predict conflict risk.

File: {scenario['file']}
Agent A intent: {scenario['intent_a']}
Agent B intent: {scenario['intent_b']}
Overlap region: {scenario['overlap_region']}

Respond with ONLY one word: CONFLICT or NO_CONFLICT"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.1
            }

            response = requests.post(self.base_url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            latency_ms = (time.time() - start) * 1000
            usage = result.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)

            # Groq free tier: effectively free, no charges
            cost_usd = 0.0

            return AgentResponse(
                agent_id=self.agent_id,
                model=self.model,
                response=result["choices"][0]["message"]["content"].strip(),
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                cost_usd=cost_usd
            )
        except Exception as e:
            print(f"GroqAgent error: {e}")
            return AgentResponse(
                agent_id=self.agent_id,
                model=self.model,
                response=f"ERROR: {str(e)}",
                tokens_used=0,
                latency_ms=(time.time() - start) * 1000,
                cost_usd=0.0
            )


class SonnetAgent:
    """Claude Sonnet - throttled to control costs"""

    def __init__(self, max_calls: int = 5):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = "claude-3-5-sonnet-20241022"
        self.agent_id = "sonnet-throttled"
        self.calls_remaining = max_calls
        self.max_calls = max_calls

        if not self.api_key:
            print("⚠️  ANTHROPIC_API_KEY not set. Set with: export ANTHROPIC_API_KEY='your_key'")

    def check_conflict(self, scenario: Dict[str, Any]) -> AgentResponse:
        """Analyze conflict risk using Sonnet (throttled)"""

        # Skip if throttle exceeded
        if self.calls_remaining <= 0:
            return AgentResponse(
                agent_id=self.agent_id,
                model=self.model,
                response="THROTTLED",
                tokens_used=0,
                latency_ms=0,
                cost_usd=0.0
            )

        self.calls_remaining -= 1

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            start = time.time()

            prompt = f"""Analyze this code coordination scenario and predict conflict risk.

File: {scenario['file']}
Agent A intent: {scenario['intent_a']}
Agent B intent: {scenario['intent_b']}
Overlap region: {scenario['overlap_region']}

Respond with ONLY one word: CONFLICT or NO_CONFLICT"""

            response = client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )

            latency_ms = (time.time() - start) * 1000
            usage = response.usage
            tokens_used = usage.input_tokens + usage.output_tokens

            # Rough cost estimate: $3/1M input, $15/1M output
            cost_usd = (usage.input_tokens * 3 + usage.output_tokens * 15) / 1_000_000

            return AgentResponse(
                agent_id=self.agent_id,
                model=self.model,
                response=response.content[0].text.strip(),
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                cost_usd=cost_usd
            )
        except Exception as e:
            print(f"SonnetAgent error: {e}")
            return AgentResponse(
                agent_id=self.agent_id,
                model=self.model,
                response=f"ERROR: {str(e)}",
                tokens_used=0,
                latency_ms=0,
                cost_usd=0.0
            )

    def remaining_calls(self) -> int:
        return self.calls_remaining
