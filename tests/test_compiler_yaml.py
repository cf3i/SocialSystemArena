from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from mas_engine.core.errors import SpecError
from mas_engine.spec.compiler import compile_spec


class CompilerYamlTests(TestCase):
    def test_compile_yaml_spec(self) -> None:
        content = """
meta:
  id: yaml_demo
  name: yaml demo
  version: 0.1.0
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
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "demo.yaml"
            path.write_text(content, encoding="utf-8")
            spec = compile_spec(path)

        self.assertEqual(spec.meta.id, "yaml_demo")
        self.assertEqual(spec.entry_stage, "a")
        self.assertEqual(len(spec.stages), 2)

    def test_yaml_root_must_be_object(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.yaml"
            path.write_text("- just\n- a\n- list\n", encoding="utf-8")
            with self.assertRaises(SpecError):
                compile_spec(path)

