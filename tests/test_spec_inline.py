"""Tests for inline spec compile helpers."""

from __future__ import annotations

import unittest

from mas_engine.core.errors import SpecError
from mas_engine.spec.compiler import compile_spec_text, dump_spec_yaml


class SpecInlineTests(unittest.TestCase):
    def test_compile_yaml_text(self) -> None:
        text = """
meta:
  id: inline_demo
  name: Inline Demo
  version: "0.1.0"
  pattern: pipeline
entry_stage: a
agents:
  x:
    runtime_id: x
stages:
  - id: a
    kind: planner
    agent: x
    transitions:
      - decision: next
        to: done
  - id: done
    kind: terminal
"""
        spec = compile_spec_text(text, fmt="yaml")
        self.assertEqual(spec.meta.id, "inline_demo")
        self.assertEqual(spec.entry_stage, "a")

    def test_dump_yaml(self) -> None:
        raw = {
            "meta": {
                "id": "x",
                "name": "X",
                "version": "0.1.0",
                "pattern": "pipeline",
            },
            "entry_stage": "a",
            "agents": {"x": {"runtime_id": "x"}},
            "stages": [
                {"id": "a", "kind": "planner", "agent": "x", "transitions": [{"decision": "next", "to": "done"}]},
                {"id": "done", "kind": "terminal"},
            ],
        }
        out = dump_spec_yaml(raw)
        self.assertIn("meta:", out)
        self.assertIn("entry_stage:", out)

    def test_compile_text_invalid(self) -> None:
        with self.assertRaises(SpecError):
            compile_spec_text("not: [valid", fmt="yaml")


if __name__ == "__main__":
    unittest.main()

