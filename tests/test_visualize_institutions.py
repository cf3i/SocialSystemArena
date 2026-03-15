from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "visualize_institutions.py"
SAMPLE_YAML = (
    ROOT / "systems" / "institutions" / "athens_democracy" / "athens_democracy.yaml"
)
US_FEDERAL_YAML = (
    ROOT / "systems" / "institutions" / "us_federal" / "us_federal_gated.yaml"
)
PIL_AVAILABLE = importlib.util.find_spec("PIL") is not None


def load_script_module():
    spec = importlib.util.spec_from_file_location("visualize_institutions", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VisualizeInstitutionsImportTests(TestCase):
    def test_script_no_longer_imports_graphviz(self) -> None:
        tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module.split(".")[0])

        self.assertNotIn("graphviz", imported_modules)


@skipUnless(PIL_AVAILABLE, "Pillow not installed")
class VisualizeInstitutionsRenderTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script_module()

    def test_render_yaml_writes_png_and_svg(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            self.module.render_yaml(SAMPLE_YAML, out_dir, fmt="png")
            self.module.render_yaml(SAMPLE_YAML, out_dir, fmt="svg")

            png_path = out_dir / "athens_democracy.png"
            svg_path = out_dir / "athens_democracy.svg"

            self.assertTrue(png_path.exists())
            self.assertTrue(svg_path.exists())
            self.assertGreater(png_path.stat().st_size, 0)
            self.assertGreater(svg_path.stat().st_size, 0)

    def test_us_federal_svg_uses_agent_labels_instead_of_stage_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            self.module.render_yaml(US_FEDERAL_YAML, out_dir, fmt="svg")
            svg = (out_dir / "us_federal_gated.svg").read_text(encoding="utf-8")

            self.assertIn("<title>legislator</title>", svg)
            self.assertIn("<title>committee</title>", svg)
            self.assertNotIn("<title>legislator_initiative</title>", svg)
            self.assertNotIn("<title>committee_modify</title>", svg)
            self.assertIn("stage: legislator_initiative", svg)
            self.assertIn("stage: completed", svg)

    def test_decision_labels_show_all_decisions(self) -> None:
        self.assertEqual(self.module.decision_label(("approve", "default")), "approve | default")
        self.assertEqual(self.module.decision_label(("approve", "next")), "approve | next")
        self.assertEqual(self.module.decision_label(("",)), "next")
        self.assertEqual(
            self.module.decision_label(("approve", "imperial_override")),
            "approve | imperial override",
        )
        self.assertEqual(
            self.module.decision_label(("approve", "invalidate", "default")),
            "approve | invalidate | default",
        )

    def test_athens_svg_expands_consensus_voters_and_completed_node(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            self.module.render_yaml(SAMPLE_YAML, out_dir, fmt="svg")
            svg = (out_dir / "athens_democracy.svg").read_text(encoding="utf-8")

            self.assertIn("<title>citizen_01</title>", svg)
            self.assertIn("<title>citizen_07</title>", svg)
            self.assertIn("<title>__terminal__</title>", svg)
            self.assertIn("stage: ekklesia_vote", svg)
