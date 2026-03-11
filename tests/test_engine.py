from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mas_engine.adapters.mock import MockAdapter
from mas_engine.core.errors import SpecError
from mas_engine.core.runtime import GovernanceRuntime
from mas_engine.spec.compiler import compile_spec


ROOT = Path(__file__).resolve().parent.parent
SYSTEMS = ROOT / "systems"


class EngineTests(unittest.TestCase):
    def test_all_sample_specs_compile(self) -> None:
        spec_files = [
            SYSTEMS / "egypt_pipeline.json",
            SYSTEMS / "qinhan_junxian.json",
            SYSTEMS / "tang_sanshengliubu.json",
            SYSTEMS / "edo_cluster.json",
            SYSTEMS / "athens_consensus.json",
            SYSTEMS / "us_federal_gated.json",
        ]
        for f in spec_files:
            spec = compile_spec(f)
            self.assertTrue(spec.meta.id)
            self.assertTrue(spec.stages)

    def test_tang_gated_pipeline_reject_then_approve(self) -> None:
        spec = compile_spec(SYSTEMS / "tang_sanshengliubu.json")
        adapter = MockAdapter(
            scripted_decisions={
                "taizi": ["work_order"],
                "zhongshu": ["submit", "submit", "approve"],
                "menxia": ["reject", "approve"],
                "shangshu": ["dispatched"],
                "hubu": ["success"],
                "libu": ["success"],
                "bingbu": ["success"],
                "xingbu": ["success"],
                "gongbu": ["success"],
                "libu_hr": ["success"],
            }
        )
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="T-001",
            title="测试三省六部",
            input_text="请完成一个复杂任务",
            max_steps=20,
        )
        self.assertEqual(state.status, "done")
        decisions = [e.decision for e in state.history if e.stage_id == "menxia_gate"]
        self.assertEqual(decisions[:2], ["reject", "approve"])

    def test_consensus_reject_path(self) -> None:
        spec = compile_spec(SYSTEMS / "athens_consensus.json")
        adapter = MockAdapter(
            scripted_decisions={
                "boule": ["next"],
                "citizen_a": ["yes"],
                "citizen_b": ["no"],
                "citizen_c": ["no"],
            }
        )
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="C-001",
            title="是否远征",
            input_text="讨论对外远征提案",
            max_steps=10,
        )
        self.assertEqual(state.status, "done")
        vote_events = [e for e in state.history if e.stage_id == "ekklesia_vote"]
        self.assertTrue(vote_events)
        self.assertEqual(vote_events[0].decision, "reject")

    def test_pipeline_cannot_have_gate(self) -> None:
        bad = {
            "meta": {
                "id": "bad_pipeline",
                "name": "bad",
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
                    "kind": "gate",
                    "agent": "x",
                    "transitions": [{"decision": "next", "to": "b"}],
                },
                {"id": "b", "kind": "terminal"},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text(json.dumps(bad))
            with self.assertRaises(SpecError):
                compile_spec(path)

    def test_qinhan_pipeline_with_monitor_feature(self) -> None:
        spec = compile_spec(SYSTEMS / "qinhan_junxian.json")
        rt = GovernanceRuntime(spec=spec, adapter=MockAdapter())
        state = rt.run(
            task_id="QH-001",
            title="推行新税制",
            input_text="皇帝要求郡县体系执行新税政",
            max_steps=10,
        )
        self.assertEqual(state.status, "done")
        self.assertEqual(
            [e.stage_id for e in state.history],
            ["huangdi_decree", "chengxiang_plan", "jun_dispatch", "xian_execute"],
        )
        for event in state.history:
            monitor = event.meta.get("monitor", [])
            self.assertTrue(monitor)
            self.assertEqual(monitor[0].get("stage"), event.stage_id)


if __name__ == "__main__":
    unittest.main()
