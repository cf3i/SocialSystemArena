from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mas_engine.spec.compiler import compile_spec


class CompilerCueTests(TestCase):
    def test_compile_cue_uses_filename_with_parent_cwd(self) -> None:
        exported = {
            "meta": {
                "id": "cue_demo",
                "name": "cue demo",
                "version": "0.1.0",
                "pattern": "pipeline",
            },
            "entry_stage": "a",
            "agents": {
                "x": {"runtime_id": "x"},
            },
            "stages": [
                {
                    "id": "a",
                    "kind": "planner",
                    "agent": "x",
                    "prompt_template": "legacy prompt",
                    "transitions": [{"decision": "next", "to": "done"}],
                },
                {"id": "done", "kind": "terminal"},
            ],
        }

        called: dict[str, object] = {}

        def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            called["cmd"] = cmd
            called["cwd"] = kwargs.get("cwd")
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(exported),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            systems = root / "systems"
            systems.mkdir()
            cue_file = systems / "demo.cue"
            cue_file.write_text("meta: { id: \"x\" }\n")

            old = os.getcwd()
            os.chdir(root)
            try:
                with patch("mas_engine.spec.compiler.subprocess.run", side_effect=_fake_run):
                    spec = compile_spec("systems/demo.cue")
            finally:
                os.chdir(old)

        self.assertEqual(spec.meta.id, "cue_demo")
        self.assertEqual(called["cmd"], ["cue", "export", "demo.cue", "--out", "json"])
        self.assertEqual(Path(str(called["cwd"])).resolve(), systems.resolve())
