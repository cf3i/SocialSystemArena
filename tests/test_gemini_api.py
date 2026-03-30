"""Live test: verify Gemini API connectivity via OpenAI-compatible endpoint.

Run with:
    python tests/test_gemini_api.py
"""
from __future__ import annotations

import sys
import os
import importlib.util

# Allow importing pc-agent-loop directly
PC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "third_party", "pc-agent-loop"))
sys.path.insert(0, PC_ROOT)

# Load mykey_gemini as mykey so llmcore can authenticate
mykey_path = os.path.join(PC_ROOT, "mykey_gemini.py")
spec = importlib.util.spec_from_file_location("mykey", mykey_path)
mykey_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mykey_mod)
sys.modules["mykey"] = mykey_mod

from llmcore import LLMSession


def test_basic_chat():
    """Send a simple prompt and verify we get a non-empty response."""
    cfg = mykey_mod.oai_config

    session = LLMSession(cfg)

    messages = [{"role": "user", "content": "Say hello in exactly 5 words."}]

    print(f"Model:  {cfg['model']}")
    print(f"Base:   {cfg['apibase']}")
    print("Sending prompt...")

    chunks = list(session.raw_ask(messages))
    response = "".join(chunks)

    print(f"Response: {response!r}")

    assert len(response.strip()) > 0, "Empty response from Gemini API"
    print("PASS: got non-empty response")

    if session._last_usage:
        pt = session._last_usage.get("prompt_tokens", 0)
        ct = session._last_usage.get("completion_tokens", 0)
        print(f"Usage: prompt_tokens={pt}  completion_tokens={ct}  total={pt+ct}")
    else:
        print("INFO: _last_usage not populated (Gemini may not return usage in stream)")


def test_multi_turn():
    """Verify multi-turn conversation works."""
    cfg = mykey_mod.oai_config

    session = LLMSession(cfg)

    messages = [
        {"role": "user", "content": "Remember this number: 42"},
    ]

    print("Turn 1: sending number...")
    chunks = list(session.raw_ask(messages))
    reply1 = "".join(chunks)
    print(f"  Reply: {reply1!r}")

    messages.append({"role": "assistant", "content": reply1})
    messages.append({"role": "user", "content": "What number did I just tell you?"})

    print("Turn 2: asking recall...")
    chunks = list(session.raw_ask(messages))
    reply2 = "".join(chunks)
    print(f"  Reply: {reply2!r}")

    assert "42" in reply2, f"Expected '42' in reply, got: {reply2!r}"
    print("PASS: multi-turn recall works")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: Basic Gemini Chat")
    print("=" * 60)
    test_basic_chat()

    print()
    print("=" * 60)
    print("Test 2: Multi-turn Conversation")
    print("=" * 60)
    test_multi_turn()
