from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mas_engine.adapters.mock import MockAdapter
from mas_engine.core.errors import SpecError
from mas_engine.core.runtime import GovernanceRuntime
from mas_engine.core.types import TaskState
from mas_engine.spec.compiler import compile_spec
from mas_engine.storage.jsonl import JsonlStore


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
            SYSTEMS / "athens_democracy.yaml",
            SYSTEMS / "qinhan_junxian.yaml",
            SYSTEMS / "tang_sanshengliubu.yaml",
            SYSTEMS / "mongol_empire.yaml",
            SYSTEMS / "us_federal_gated.yaml",
            SYSTEMS / "soviet_party_state.yaml",
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

    def test_prompt_contains_topology_context(self) -> None:
        spec = compile_spec(SYSTEMS / "tang_sanshengliubu.json")
        rt = GovernanceRuntime(spec=spec, adapter=MockAdapter())
        stage = next(s for s in spec.stages if s.id == spec.entry_stage)
        task = TaskState(
            task_id="T-CTX",
            title="拓扑透传",
            input_text="测试",
            current_stage=spec.entry_stage,
            shared_state={"banned_terms": []},
        )
        prompt = rt._build_prompt(task, stage)
        self.assertIn("transitions", prompt)
        self.assertIn("allowed_decisions", prompt)

    def test_trace_has_agent_rows_with_sequential_id(self) -> None:
        spec = compile_spec(SYSTEMS / "egypt_pipeline.json")
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            rt = GovernanceRuntime(
                spec=spec,
                adapter=MockAdapter(),
                store=JsonlStore(trace_path),
            )
            state = rt.run(
                task_id="E-SEQ-001",
                title="计算",
                input_text="1*3*5",
                max_steps=10,
            )
            self.assertEqual(state.status, "done")
            rows = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        agent_rows = [r for r in rows if r.get("record_type") == "agent_trace"]
        self.assertEqual(len(agent_rows), 2)
        self.assertEqual(
            [r["agent_trace"]["sequential_id"] for r in agent_rows],
            [1, 2],
        )
        self.assertEqual(
            [r["agent_trace"]["stage_id"] for r in agent_rows],
            ["vizier_planning", "nomarch_execution"],
        )

    def test_consensus_trace_contains_each_voter(self) -> None:
        spec = compile_spec(SYSTEMS / "athens_consensus.json")
        adapter = MockAdapter(
            scripted_decisions={
                "boule": ["next"],
                "citizen_a": ["yes"],
                "citizen_b": ["no"],
                "citizen_c": ["no"],
            }
        )
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            rt = GovernanceRuntime(
                spec=spec,
                adapter=adapter,
                store=JsonlStore(trace_path),
            )
            state = rt.run(
                task_id="C-SEQ-001",
                title="投票",
                input_text="是否远征",
                max_steps=10,
            )
            self.assertEqual(state.status, "done")
            rows = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        agent_rows = [r for r in rows if r.get("record_type") == "agent_trace"]
        self.assertEqual(len(agent_rows), 4)  # 1 proposer + 3 voters
        self.assertEqual(
            [r["agent_trace"]["sequential_id"] for r in agent_rows],
            [1, 2, 3, 4],
        )


if __name__ == "__main__":
    unittest.main()
