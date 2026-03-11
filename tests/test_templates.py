from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from mas_engine.spec.compiler import compile_spec
from mas_engine.spec.templates import SUPPORTED_PATTERNS, build_spec_template


class TemplateTests(TestCase):
    def test_all_pattern_templates_compile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            for pattern in SUPPORTED_PATTERNS:
                raw = build_spec_template(
                    spec_id=f"tmpl_{pattern}",
                    name=f"Template {pattern}",
                    pattern=pattern,
                )
                spec_path = base / f"{pattern}.json"
                spec_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2))

                spec = compile_spec(spec_path)
                self.assertEqual(spec.meta.pattern, pattern)
                self.assertTrue(spec.stages)
                self.assertTrue(spec.agents)

    def test_invalid_pattern_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_spec_template(spec_id="x", name="x", pattern="bad")
