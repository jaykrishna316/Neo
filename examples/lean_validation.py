"""
Neo MVP Validation Test Harness
Run with: python3 lean_validation.py
Cost: ~$2-3 total (local + Groq free + Sonnet throttled)
"""

import json
import time
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import sys

from lean_agents import LocalAgent, GroqAgent, SonnetAgent, AgentResponse
from lean_scenarios import generate_scenarios, scenarios_by_type


@dataclass
class ValidationResult:
    scenario_id: str
    file: str
    expected_result: str
    agent_responses: Dict[str, str]
    agent_latencies: Dict[str, float]
    agent_costs: Dict[str, float]
    accuracy: float  # How many agents got it right
    consensus: str  # CONFLICT or NO_CONFLICT (majority vote)


class MetricsCollector:
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.total_tokens = 0
        self.total_cost = 0.0
        self.total_latency = 0.0
        self.start_time = time.time()

    def add_result(self, result: ValidationResult):
        self.results.append(result)
        for cost in result.agent_costs.values():
            self.total_cost += cost
        for latency in result.agent_latencies.values():
            self.total_latency += latency

    def accuracy(self) -> float:
        """Overall accuracy: % of correct predictions"""
        if not self.results:
            return 0.0
        correct = sum(1 for r in self.results if r.consensus == r.expected_result)
        return (correct / len(self.results)) * 100

    def false_positive_rate(self) -> float:
        """% predicted CONFLICT when actually NO_CONFLICT"""
        if not self.results:
            return 0.0
        fp = sum(1 for r in self.results
                if r.consensus == "CONFLICT" and r.expected_result == "NO_CONFLICT")
        total_no_conflict = sum(1 for r in self.results if r.expected_result == "NO_CONFLICT")
        return (fp / total_no_conflict * 100) if total_no_conflict > 0 else 0.0

    def false_negative_rate(self) -> float:
        """% predicted NO_CONFLICT when actually CONFLICT"""
        if not self.results:
            return 0.0
        fn = sum(1 for r in self.results
                if r.consensus == "NO_CONFLICT" and r.expected_result == "CONFLICT")
        total_conflict = sum(1 for r in self.results if r.expected_result == "CONFLICT")
        return (fn / total_conflict * 100) if total_conflict > 0 else 0.0

    def avg_latency_ms(self) -> float:
        """Average latency across all agents"""
        if not self.results or not self.results[0].agent_latencies:
            return 0.0
        total_latencies = sum(sum(r.agent_latencies.values()) for r in self.results)
        total_latency_points = sum(len(r.agent_latencies) for r in self.results)
        return total_latencies / total_latency_points if total_latency_points > 0 else 0.0

    def cost_per_scenario(self) -> float:
        """Average cost per scenario tested"""
        if not self.results:
            return 0.0
        return self.total_cost / len(self.results)

    def print_report(self):
        """Print validation report"""
        elapsed = time.time() - self.start_time

        print("\n" + "="*70)
        print("NEO MVP VALIDATION RESULTS")
        print("="*70)
        print(f"\n📊 ACCURACY METRICS")
        print(f"  Overall Accuracy:        {self.accuracy():.1f}%")
        print(f"  False Positive Rate:     {self.false_positive_rate():.1f}%")
        print(f"  False Negative Rate:     {self.false_negative_rate():.1f}%")
        print(f"  Total Scenarios:         {len(self.results)}")
        print(f"\n⚡ PERFORMANCE METRICS")
        print(f"  Avg Latency (p50):       {self.avg_latency_ms():.0f}ms")
        print(f"  Total Time:              {elapsed:.1f}s")
        print(f"\n💰 COST METRICS")
        print(f"  Total Cost:              ${self.total_cost:.2f}")
        print(f"  Cost per Scenario:       ${self.cost_per_scenario():.4f}")
        print(f"  Budget Used:             {(self.total_cost/3)*100:.1f}% of $3 budget")
        print(f"\n🤖 AGENT STATUS")

        if self.results and self.results[0].agent_costs:
            agent_costs = {}
            for r in self.results:
                for agent, cost in r.agent_costs.items():
                    if agent not in agent_costs:
                        agent_costs[agent] = 0.0
                    agent_costs[agent] += cost

            for agent, cost in agent_costs.items():
                print(f"  {agent}: ${cost:.3f}")

        print(f"\n✅ CONCLUSION")
        if self.accuracy() >= 90:
            print(f"  ✓ Neo coordination is production-ready")
            print(f"  ✓ Accuracy meets enterprise threshold (>90%)")
        else:
            print(f"  ⚠ Neo needs tuning (accuracy < 90%)")

        print("="*70 + "\n")


def get_consensus(responses: Dict[str, str]) -> str:
    """Get majority consensus from agent responses"""
    valid_responses = [r for r in responses.values() if r in ["CONFLICT", "NO_CONFLICT"]]
    if not valid_responses:
        return "UNKNOWN"
    conflict_count = sum(1 for r in valid_responses if r == "CONFLICT")
    return "CONFLICT" if conflict_count > len(valid_responses) / 2 else "NO_CONFLICT"


def run_validation(num_scenarios: int = 100, use_sonnet: bool = True):
    """Run full validation suite"""

    print("\n🚀 NEO MVP VALIDATION STARTING")
    print(f"   Scenarios: {num_scenarios}")
    print(f"   Agents: Local + Groq + {'Sonnet (throttled)' if use_sonnet else 'Groq only'}")
    print(f"   Cost estimate: <$3\n")

    # Initialize agents
    local_agent = LocalAgent(model="qwen2.5:3b")
    groq_agent = GroqAgent()
    sonnet_agent = SonnetAgent(max_calls=5) if use_sonnet else None

    # Generate scenarios
    scenarios = generate_scenarios()[:num_scenarios]

    # Collect metrics
    metrics = MetricsCollector()

    # Run validation
    print(f"Running {len(scenarios)} scenarios...\n")

    for i, scenario in enumerate(scenarios):
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{len(scenarios)} scenarios...")

        # Get responses from all agents
        responses = {}
        latencies = {}
        costs = {}

        # Local agent
        local_resp = local_agent.check_conflict(scenario)
        if local_resp.response != "ERROR":
            responses["local"] = local_resp.response
            latencies["local"] = local_resp.latency_ms
            costs["local"] = local_resp.cost_usd

        # Groq agent
        groq_resp = groq_agent.check_conflict(scenario)
        if groq_resp.response != "ERROR":
            responses["groq"] = groq_resp.response
            latencies["groq"] = groq_resp.latency_ms
            costs["groq"] = groq_resp.cost_usd

        # Sonnet agent (throttled)
        if sonnet_agent and sonnet_agent.remaining_calls() > 0:
            sonnet_resp = sonnet_agent.check_conflict(scenario)
            if sonnet_resp.response not in ["ERROR", "THROTTLED"]:
                responses["sonnet"] = sonnet_resp.response
                latencies["sonnet"] = sonnet_resp.latency_ms
                costs["sonnet"] = sonnet_resp.cost_usd

        # Calculate accuracy (how many agents got it right)
        expected = scenario["expected"]
        correct = sum(1 for resp in responses.values() if resp == expected)
        accuracy = (correct / len(responses) * 100) if responses else 0.0

        # Get consensus
        consensus = get_consensus(responses)

        # Record result
        result = ValidationResult(
            scenario_id=scenario["id"],
            file=scenario["file"],
            expected_result=expected,
            agent_responses=responses,
            agent_latencies=latencies,
            agent_costs=costs,
            accuracy=accuracy,
            consensus=consensus
        )

        metrics.add_result(result)

    # Print report
    metrics.print_report()

    # Save detailed results
    results_file = "neo_validation_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "summary": {
                "total_scenarios": len(scenarios),
                "accuracy": metrics.accuracy(),
                "false_positive_rate": metrics.false_positive_rate(),
                "false_negative_rate": metrics.false_negative_rate(),
                "total_cost": metrics.total_cost,
                "avg_latency_ms": metrics.avg_latency_ms()
            },
            "results": [asdict(r) for r in metrics.results]
        }, f, indent=2)

    print(f"📁 Results saved to: {results_file}")
    print(f"\n✅ Validation complete!")

    return metrics


if __name__ == "__main__":
    # Check prerequisites
    try:
        import requests
        print("✓ requests installed")
    except ImportError:
        print("❌ Install requirements: pip install requests anthropic groq")
        sys.exit(1)

    # Run validation
    metrics = run_validation(num_scenarios=100, use_sonnet=True)

    # Exit with status
    if metrics.accuracy() >= 90:
        print("\n🎉 Validation passed! Neo is ready for enterprise testing.")
        sys.exit(0)
    else:
        print("\n⚠️  Validation needs improvement. Review results.")
        sys.exit(1)
