from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mas_engine.adapters.openclaw import OpenClawAdapter, _parse_agent_output
from mas_engine.core.errors import AdapterError


class OpenClawAdapterTests(TestCase):
    def test_parse_agent_output_uses_last_decision_object(self) -> None:
        out = (
            "log before\n"
            '{"status":"running"}\n'
            '{"decision":"reject","summary":"first"}\n'
            "more logs\n"
            '{"decision":"approve","summary":"final","updates":{"x":1},"meta":{"k":"v"}}\n'
        )
        result = _parse_agent_output(out)
        self.assertEqual(result.decision, "approve")
        self.assertEqual(result.summary, "final")
        self.assertEqual(result.updates, {"x": 1})
        self.assertEqual(result.meta, {"k": "v"})

    def test_parse_agent_output_plain_text_fallback(self) -> None:
        result = _parse_agent_output("line1\nline2")
        self.assertEqual(result.decision, "next")
        self.assertEqual(result.summary, "line2")

    def test_auto_deliver_mode_falls_back_without_deliver_flag(self) -> None:
        calls: list[list[str]] = []

        def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            del kwargs
            calls.append(cmd)
            if "--deliver" in cmd:
                return SimpleNamespace(returncode=2, stdout="", stderr="unknown flag: --deliver")
            return SimpleNamespace(
                returncode=0,
                stdout='{"decision":"approve","summary":"ok","updates":{}}',
                stderr="",
            )

        adapter = OpenClawAdapter(deliver_mode="auto")
        with patch("mas_engine.adapters.openclaw.subprocess.run", side_effect=_fake_run):
            result = adapter.dispatch(runtime_id="zhongshu", message="hello", timeout_sec=3, retries=1)

        self.assertEqual(result.decision, "approve")
        self.assertEqual(len(calls), 2)
        self.assertIn("--deliver", calls[0])
        self.assertNotIn("--deliver", calls[1])

    def test_invalid_deliver_mode_raises(self) -> None:
        adapter = OpenClawAdapter(deliver_mode="bad")
        with self.assertRaises(AdapterError):
            adapter.dispatch(runtime_id="x", message="x")
