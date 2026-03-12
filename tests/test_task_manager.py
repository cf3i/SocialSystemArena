"""Tests for dashboard task manager."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from mas_engine.observability.task_manager import TaskRunManager

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = ROOT / "systems"


class TaskManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_cwd = Path.cwd()
        os.chdir(ROOT)

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)

    def test_start_run_and_collect_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = TaskRunManager(
                trace_dir=td,
                institutions_path=SYSTEMS / "institutions.yaml",
            )
            task = manager.start_run(
                {
                    "spec": str(
                        SYSTEMS / "institutions" / "egypt_pipeline" / "egypt_pipeline.json"
                    ),
                    "title": "计算",
                    "input": "1*3*5",
                    "adapter": "mock",
                }
            )
            task_id = task["task_id"]

            for _ in range(80):
                cur = manager.get_task(task_id)
                if cur.get("status") in {"done", "error", "max_steps_exceeded"}:
                    break
                time.sleep(0.05)
            else:
                self.fail("task did not finish in time")

            final = manager.get_task(task_id)
            self.assertEqual(final["status"], "done")
            self.assertGreaterEqual(final["steps"], 2)
            self.assertTrue(Path(final["trace_out"]).exists())

            events = manager.get_events(task_id, since_seq=0, limit=0)
            kinds = {e.get("record_type") for e in events}
            self.assertIn("lifecycle", kinds)
            self.assertIn("stage_event", kinds)
            self.assertIn("agent_trace", kinds)

    def test_start_run_by_institution_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = TaskRunManager(
                trace_dir=td,
                institutions_path=SYSTEMS / "institutions.yaml",
            )
            task = manager.start_run(
                {
                    "institution_id": "qinhan_junxian",
                    "title": "县政测试",
                    "input": "执行政令",
                    "adapter": "mock",
                }
            )
            task_id = task["task_id"]
            for _ in range(80):
                cur = manager.get_task(task_id)
                if cur.get("status") in {"done", "error", "max_steps_exceeded"}:
                    break
                time.sleep(0.05)
            final = manager.get_task(task_id)
            self.assertEqual(final["institution_id"], "qinhan_junxian")
            self.assertEqual(final["status"], "done")
            self.assertTrue(
                final["spec_path"].endswith(
                    "systems/institutions/qinhan_junxian/qinhan_junxian.yaml"
                )
            )

    def test_inline_yaml_validate_and_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manager = TaskRunManager(
                trace_dir=td,
                institutions_path=SYSTEMS / "institutions.yaml",
            )
            spec = manager.get_spec_text("egypt_yaml")
            spec_text = spec["spec_text"]

            checked = manager.validate_spec_payload(
                {"spec_inline": spec_text, "spec_format": "yaml"}
            )
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["meta"]["id"], "egypt_pipeline_yaml")

            task = manager.start_run(
                {
                    "spec_inline": spec_text,
                    "spec_format": "yaml",
                    "title": "inline run",
                    "input": "计算",
                    "adapter": "mock",
                }
            )
            task_id = task["task_id"]
            for _ in range(80):
                cur = manager.get_task(task_id)
                if cur.get("status") in {"done", "error", "max_steps_exceeded"}:
                    break
                time.sleep(0.05)
            final = manager.get_task(task_id)
            self.assertEqual(final["status"], "done")
            self.assertEqual(final["spec_source"], "inline_text")

    def test_institutions_registry_api(self) -> None:
        manager = TaskRunManager(
            trace_dir="traces",
            institutions_path=SYSTEMS / "institutions.yaml",
        )
        items = manager.list_institutions()
        ids = {x["institution_id"] for x in items}
        self.assertIn("athens_democracy", ids)
        self.assertIn("tang_sanshengliubu", ids)

        tang = manager.get_institution("tang_sanshengliubu")
        self.assertEqual(tang["institution_name"], "唐朝三省六部")
        self.assertTrue(tang.get("institution_name_en"))
        self.assertTrue(tang["specs"])
        self.assertTrue(tang["specs"][0].get("spec_name_en"))

        spec = manager.get_spec_text(tang["default_spec_id"])
        self.assertIn("spec_text", spec)
        self.assertIn("topology", spec)

    def test_preview_topology(self) -> None:
        manager = TaskRunManager(
            trace_dir="traces",
            institutions_path=SYSTEMS / "institutions.yaml",
        )
        topology = manager.preview_topology(
            str(
                SYSTEMS
                / "institutions"
                / "qinhan_junxian"
                / "qinhan_junxian.yaml"
            )
        )
        self.assertIn("nodes", topology)
        self.assertIn("edges", topology)
        self.assertTrue(topology["entry_stage"])

    def test_save_institution_spec(self) -> None:
        spec_text = """
meta:
  id: new_demo_spec
  name: New Demo Spec
  version: "0.1.0"
  pattern: pipeline
  description: created in test
entry_stage: plan
agents:
  planner:
    runtime_id: planner
stages:
  - id: plan
    kind: planner
    agent: planner
    prompt_template: legacy prompt
    transitions:
      - decision: next
        to: completed
  - id: completed
    kind: terminal
"""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            systems_dir = tdp / "systems"
            systems_dir.mkdir(parents=True, exist_ok=True)
            registry = systems_dir / "institutions.yaml"
            registry.write_text("institutions: []\n", encoding="utf-8")

            manager = TaskRunManager(
                trace_dir=(tdp / "traces"),
                institutions_path=registry,
            )
            out = manager.save_institution_spec(
                {
                    "institution_id": "new_institution",
                    "institution_name": "新制度",
                    "spec_id": "new_demo_spec",
                    "spec_name": "新制度Spec",
                    "spec_text": spec_text,
                    "spec_format": "yaml",
                    "set_default": True,
                }
            )
            self.assertTrue(out["ok"])
            self.assertEqual(out["institution"]["institution_id"], "new_institution")
            self.assertEqual(out["institution"]["institution_name_en"], "新制度")
            self.assertEqual(out["spec"]["spec_id"], "new_demo_spec")
            self.assertTrue(Path(out["spec"]["spec_path"]).exists())

            rows = manager.list_institutions()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["institution_id"], "new_institution")


if __name__ == "__main__":
    unittest.main()
