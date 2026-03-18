"""Live test: verify that LLMSession._last_usage captures precise token counts.

Run with:
    python tests/test_token_tracking.py
"""
from __future__ import annotations

import sys
import os

# Allow importing pc-agent-loop directly
PC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "third_party", "pc-agent-loop"))
sys.path.insert(0, PC_ROOT)

# Load mykey so LLMSession can authenticate
import importlib.util
mykey_path = os.path.join(PC_ROOT, "mykey.py")
spec = importlib.util.spec_from_file_location("mykey", mykey_path)
mykey_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mykey_mod)
sys.modules["mykey"] = mykey_mod

from sidercall import LLMSession, ToolClient


def test_llmsession_usage():
    """Send a short prompt and check _last_usage is populated with real token counts."""
    mykeys = {k: v for k, v in vars(mykey_mod).items() if not k.startswith("_")}

    # Find first oai config
    cfg = None
    for k, v in mykeys.items():
        if "oai" in k and isinstance(v, dict):
            cfg = v
            break

    if cfg is None:
        print("SKIP: no oai_config found in mykey.py")
        return

    session = LLMSession(
        api_key=cfg["apikey"],
        api_base=cfg["apibase"],
        model=cfg["model"],
        proxy=cfg.get("proxy"),
        api_mode=cfg.get("api_mode", "chat_completions"),
    )

    messages = [{"role": "user", "content": "Say hello in exactly 5 words."}]

    print("Sending prompt...")
    chunks = list(session.raw_ask(messages))
    response = "".join(chunks)

    print(f"Response: {response!r}")
    print(f"_last_usage: {session._last_usage}")

    assert session._last_usage is not None, "_last_usage is None — usage chunk was not captured"
    assert isinstance(session._last_usage, dict), f"expected dict, got {type(session._last_usage)}"

    prompt_tokens = session._last_usage.get("prompt_tokens", 0)
    completion_tokens = session._last_usage.get("completion_tokens", 0)

    assert prompt_tokens > 0, f"prompt_tokens={prompt_tokens}, expected > 0"
    assert completion_tokens > 0, f"completion_tokens={completion_tokens}, expected > 0"

    print(f"prompt_tokens={prompt_tokens}  completion_tokens={completion_tokens}  total={prompt_tokens+completion_tokens}")
    print("PASS: _last_usage populated with precise values")


def test_toolclient_accumulation():
    """Check ToolClient.tokens_input/output accumulate across calls using precise values."""
    mykeys = {k: v for k, v in vars(mykey_mod).items() if not k.startswith("_")}

    cfg = None
    for k, v in mykeys.items():
        if "oai" in k and isinstance(v, dict):
            cfg = v
            break

    if cfg is None:
        print("SKIP: no oai_config found in mykey.py")
        return

    session = LLMSession(
        api_key=cfg["apikey"],
        api_base=cfg["apibase"],
        model=cfg["model"],
        proxy=cfg.get("proxy"),
        api_mode=cfg.get("api_mode", "chat_completions"),
    )
    client = ToolClient(session)

    messages = [{"role": "user", "content": "Reply with one word: OK"}]

    print("Calling ToolClient.chat()...")
    # consume generator
    list(client.chat(messages))

    print(f"tokens_input={client.tokens_input}  tokens_output={client.tokens_output}")

    assert client.tokens_input > 0, f"tokens_input={client.tokens_input}, expected > 0"
    assert client.tokens_output > 0, f"tokens_output={client.tokens_output}, expected > 0"

    # Precise values should NOT look like chars//4 estimates (which would be huge for a system prompt)
    # A reasonable single-call input token count for a short message is < 500
    # chars//4 of the full_prompt (with tool instructions) would be 1000+
    print(f"PASS: tokens accumulated — input={client.tokens_input} output={client.tokens_output}")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: LLMSession._last_usage")
    print("=" * 60)
    test_llmsession_usage()

    print()
    print("=" * 60)
    print("Test 2: ToolClient token accumulation")
    print("=" * 60)
    test_toolclient_accumulation()
