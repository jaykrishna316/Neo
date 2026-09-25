#!/usr/bin/env python3
"""
Diagnostic script to verify LocalAgent and GroqAgent connectivity
"""

import os
import requests
import json

print("=" * 60)
print("NEO AGENT DIAGNOSTICS")
print("=" * 60)

# 1. Check Ollama
print("\n1️⃣  OLLAMA DIAGNOSTICS")
print("-" * 60)

try:
    # Check if Ollama is running
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json().get("models", [])
        print(f"✓ Ollama is running")
        print(f"  Available models: {len(models)}")
        for model in models:
            name = model.get("name", "unknown")
            size = model.get("size", 0)
            print(f"    - {name} ({size / 1e9:.1f}GB)")

        # Pick first model to use
        if models:
            first_model = models[0].get("name", "qwen2.5:3b")
            print(f"\n  ℹ️  Will use model: {first_model}")

            # Test /api/generate with first model
            print(f"\n  Testing /api/generate with {first_model}...")
            test_response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": first_model,
                    "prompt": "Say CONFLICT or NO_CONFLICT",
                    "stream": False
                },
                timeout=30
            )
            if test_response.status_code == 200:
                print(f"  ✓ /api/generate works!")
                result = test_response.json()
                print(f"    Response: {result.get('response', '')[:50]}...")
            else:
                print(f"  ✗ /api/generate failed: {test_response.status_code}")
                print(f"    {test_response.text}")
        else:
            print("  ⚠️  No models installed in Ollama!")
            print("  Install with: ollama pull mistral")
    else:
        print(f"✗ Ollama returned status {response.status_code}")
except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to Ollama on localhost:11434")
    print("  Is Ollama running? Start with: ollama serve")
except Exception as e:
    print(f"✗ Error checking Ollama: {e}")

# 2. Check Groq
print("\n2️⃣  GROQ API DIAGNOSTICS")
print("-" * 60)

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("✗ GROQ_API_KEY environment variable not set")
    print("  Set with: export GROQ_API_KEY='your_key'")
else:
    print(f"✓ GROQ_API_KEY is set (length: {len(api_key)})")

    try:
        # List available models
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            models = response.json().get("data", [])
            print(f"✓ Groq API is reachable")
            print(f"  Available models: {len(models)}")
            for model in models[:5]:
                print(f"    - {model.get('id')}")

            # Test /chat/completions with first model
            print(f"\n  Testing /chat/completions...")
            test_response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen/qwen3.8-27b",
                    "messages": [{"role": "user", "content": "Say CONFLICT or NO_CONFLICT"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                },
                timeout=30
            )

            if test_response.status_code == 200:
                print(f"  ✓ /chat/completions works!")
                result = test_response.json()
                print(f"    Response: {result['choices'][0]['message']['content']}")
            else:
                print(f"  ✗ /chat/completions failed: {test_response.status_code}")
                print(f"    {test_response.text[:200]}")
        else:
            print(f"✗ Groq API returned status {response.status_code}")
            print(f"  {response.text[:200]}")
    except requests.exceptions.Timeout:
        print("✗ Groq API timeout - connection slow or API down")
    except Exception as e:
        print(f"✗ Error checking Groq: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTICS COMPLETE")
print("=" * 60 + "\n")
