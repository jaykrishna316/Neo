# Multi-Model Validation Tests

Real-world Neo validation using Groq API and Local Ollama.

## Quick Start

```bash
# 1. Install Ollama and start it
ollama serve

# 2. In another terminal, run diagnostics
export GROQ_API_KEY="your_groq_key"
python3 diagnose_agents.py

# 3. Run full validation
python3 lean_validation.py
```

## Files

- **lean_agents.py** - Agent implementations (LocalAgent, GroqAgent, SonnetAgent)
- **lean_scenarios.py** - 100 realistic code conflict scenarios
- **lean_validation.py** - Main test harness
- **diagnose_agents.py** - Verify Ollama and Groq are working
- **REAL_TEST_RESULTS.md** - Detailed results and analysis

## Results

**82% Accuracy** on 100 real scenarios
- LocalAgent (Ollama): Consistent, free
- GroqAgent (Groq): Rate-limited but works
- Cost: $0.00

See REAL_TEST_RESULTS.md for details.
