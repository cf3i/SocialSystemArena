from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from mas_engine.adapters.mock import MockAdapter
from mas_engine.core.errors import SpecError
from mas_engine.core.runtime import GovernanceRuntime
from mas_engine.core.types import AgentResult, TaskState
from mas_engine.spec.compiler import compile_spec
from mas_engine.storage.jsonl import JsonlStore


ROOT = Path(__file__).resolve().parent.parent
SYSTEMS = ROOT / "systems"
INSTITUTION_SPECS = SYSTEMS / "institutions"


class EngineTests(unittest.TestCase):
    def test_all_sample_specs_compile(self) -> None:
        spec_files = [
            INSTITUTION_SPECS / "egypt_pipeline" / "egypt_pipeline.json",
            INSTITUTION_SPECS / "qinhan_junxian" / "qinhan_junxian.json",
            INSTITUTION_SPECS / "tang_sanshengliubu" / "tang_sanshengliubu.json",
            INSTITUTION_SPECS / "athens_democracy" / "athens_consensus.json",
            INSTITUTION_SPECS / "us_federal" / "us_federal_gated.json",
            INSTITUTION_SPECS / "athens_democracy" / "athens_democracy.yaml",
            INSTITUTION_SPECS / "athens_democracy" / "athens_open_challenge.yaml",
            INSTITUTION_SPECS / "qinhan_junxian" / "qinhan_junxian.yaml",
            INSTITUTION_SPECS / "tang_sanshengliubu" / "tang_sanshengliubu.yaml",
            INSTITUTION_SPECS / "mongol_empire" / "mongol_empire.yaml",
            INSTITUTION_SPECS / "us_federal" / "us_federal_gated.yaml",
            INSTITUTION_SPECS / "edo_bakuhan" / "edo_bakuhan.yaml",
            INSTITUTION_SPECS / "soviet_party_state" / "soviet_party_state.yaml",
            INSTITUTION_SPECS / "soviet_party_state" / "soviet_consensus_loop.yaml",
        ]
        for f in spec_files:
            spec = compile_spec(f)
            self.assertTrue(spec.meta.id)
            self.assertTrue(spec.stages)

    def test_tang_gated_pipeline_reject_then_approve(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "tang_sanshengliubu" / "tang_sanshengliubu.json"
        )
        adapter = MockAdapter(
            scripted_decisions={
                "huangdi": ["next"],
                "zhongshu": ["submit", "submit"],
                "menxia": ["reject", "approve"],
                "shangshu": ["dispatch"],
                "hubu": ["success"],
                "libu": ["success"],
                "libu_hr": ["success"],
                "bingbu": ["success"],
                "xingbu": ["success"],
                "gongbu": ["success"],
            }
        )
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="T-001",
            title="测试三省六部",
            input_text="请完成一个复杂任务",
            max_steps=24,
        )
        self.assertEqual(state.status, "done")
        decisions = [e.decision for e in state.history if e.stage_id == "menxia_gate"]
        self.assertEqual(decisions[:2], ["reject", "approve"])

    def test_us_federal_veto_override_and_court_invalidate(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "us_federal" / "us_federal_gated.json"
        )
        adapter = MockAdapter(
            scripted_decisions={
                "legislator": ["next"],
                "committee": ["approve"],
                "house": ["approve"],
                "senate": ["approve"],
                "president": ["veto"],
                "congress_override_panel": ["approve"],
                "agency": ["next"],
                "supreme_court": ["invalidate"],
            }
        )
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="US-001",
            title="联邦法案流程测试",
            input_text="测试总统否决后的国会覆决与法院审查",
            max_steps=20,
        )
        self.assertEqual(state.status, "done")
        self.assertEqual(
            [e.stage_id for e in state.history],
            [
                "legislator_initiative",
                "committee_modify",
                "house_vote",
                "senate_vote",
                "president_veto",
                "congress_override",
                "agency_execute",
                "court_audit",
            ],
        )
        self.assertEqual(state.history[-1].decision, "invalidate")

    def test_edo_bakuhan_cluster_with_monitor_sidechannel(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "edo_bakuhan" / "edo_bakuhan.yaml"
        )
        adapter = MockAdapter(
            scripted_decisions={
                "shogun": ["next"],
                "satsuma_daimyo": ["success"],
                "choshu_daimyo": ["success"],
                "kaga_daimyo": ["success"],
                "tosa_daimyo": ["success"],
                "bakufu_roju": ["compliant"],
                "metsuke": ["ok", "ok", "ok"],
            }
        )
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="EDO-001",
            title="锁国令执行",
            input_text="幕府发布全国禁令并要求各藩回报",
            max_steps=12,
        )
        self.assertEqual(state.status, "done")
        self.assertEqual(
            [e.stage_id for e in state.history],
            ["shogun_orchestrate", "han_cluster_execute", "sankin_kotai_check"],
        )
        for event in state.history:
            monitor = event.meta.get("monitor", [])
            self.assertTrue(any(m.get("type") == "heartbeat" for m in monitor))
            reports = [m for m in monitor if m.get("type") == "observer_report"]
            self.assertTrue(reports)
            self.assertEqual(reports[0].get("observer_agent"), "metsuke")

    def test_stage_timeout_stops_pipeline_even_with_default_transition(self) -> None:
        class SlowAdapter:
            def dispatch(
                self,
                runtime_id: str,
                message: str,
                timeout_sec: int = 300,
                retries: int = 1,
            ) -> AgentResult:
                del runtime_id, message, timeout_sec, retries
                time.sleep(3)
                return AgentResult(decision="next", summary="slow")

        spec_obj = {
            "meta": {
                "id": "timeout_guard_demo",
                "name": "timeout guard demo",
                "version": "0.1.0",
                "pattern": "pipeline",
            },
            "entry_stage": "plan",
            "agents": {
                "planner": {
                    "runtime_id": "planner",
                    "timeout_sec": 1,
                    "retries": 1,
                },
            },
            "stages": [
                {
                    "id": "plan",
                    "kind": "planner",
                    "agent": "planner",
                    "prompt_template": "timeout guard test",
                    "transitions": [
                        {"decision": "next", "to": "done"},
                        {"decision": "default", "to": "done"},
                    ],
                },
                {"id": "done", "kind": "terminal"},
            ],
            "policy": {"require_json_decision": False, "max_steps": 4},
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "timeout_guard_demo.json"
            path.write_text(json.dumps(spec_obj), encoding="utf-8")
            spec = compile_spec(path)

        rt = GovernanceRuntime(spec=spec, adapter=SlowAdapter())
        state = rt.run(
            task_id="TIMEOUT-001",
            title="timeout guard",
            input_text="slow",
            max_steps=4,
        )
        self.assertEqual(state.status, "error")
        self.assertEqual(len(state.history), 1)
        self.assertEqual(state.history[0].stage_id, "plan")
        self.assertEqual(state.history[0].decision, "error")
        self.assertIn("timeout", state.history[0].summary.lower())

    def test_consensus_reject_path(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "athens_democracy" / "athens_consensus.json"
        )
        vote_stage = next(s for s in spec.stages if s.id == "ekklesia_vote")
        voters = list(vote_stage.consensus.voters if vote_stage.consensus else [])
        self.assertGreaterEqual(len(voters), 3)
        yes_voter = voters[0]
        no_voters = voters[1:]
        scripted = {"boule_planner_1": ["next"], yes_voter: ["yes"]}
        scripted.update({v: ["no"] for v in no_voters})
        adapter = MockAdapter(
            scripted_decisions=scripted
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

    def test_athens_open_challenge_variant_mid_audit_path(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "athens_democracy" / "athens_open_challenge.yaml"
        )
        vote_stage = next(s for s in spec.stages if s.id == "ekklesia_vote")
        voters = list(vote_stage.consensus.voters if vote_stage.consensus else [])
        self.assertGreaterEqual(len(voters), 3)
        scripted = {
            "random_citizen": ["next"],
            "boule_planner_1": ["approve"],
            "dikasteria_1": ["approve"],
            "strategos_1": ["next"],
        }
        scripted.update({v: ["no"] for v in voters})
        rt = GovernanceRuntime(
            spec=spec,
            adapter=MockAdapter(scripted_decisions=scripted),
        )
        state = rt.run(
            task_id="ATH-VAR-001",
            title="开放提案合法性争议",
            input_text="公民提案进入大会后触发挑战",
            max_steps=12,
        )
        self.assertEqual(state.status, "done")
        self.assertEqual(
            [e.stage_id for e in state.history],
            [
                "citizen_propose",
                "boule_gate",
                "ekklesia_vote",
                "dikasteria_audit",
                "strategos_execute",
            ],
        )
        vote_event = next(e for e in state.history if e.stage_id == "ekklesia_vote")
        self.assertEqual(vote_event.decision, "challenge")

    def test_soviet_consensus_loop_variant_feedback(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "soviet_party_state" / "soviet_consensus_loop.yaml"
        )
        vote_stage = next(s for s in spec.stages if s.id == "politburo_consensus")
        voters = list(vote_stage.consensus.voters if vote_stage.consensus else [])
        self.assertEqual(len(voters), 5)
        scripted = {
            "sovmin": ["next", "next"],
            "gosplan": ["next", "next"],
            "republic_exec": ["report_deviation", "next"],
            "supreme_soviet": ["next"],
        }
        scripted.update({v: ["yes", "yes"] for v in voters})
        rt = GovernanceRuntime(
            spec=spec,
            adapter=MockAdapter(scripted_decisions=scripted),
        )
        state = rt.run(
            task_id="SOV-VAR-001",
            title="执行偏差回环",
            input_text="地方执行偏差触发政治局复议",
            max_steps=20,
        )
        self.assertEqual(state.status, "done")
        consensus_events = [e for e in state.history if e.stage_id == "politburo_consensus"]
        self.assertEqual(len(consensus_events), 2)
        self.assertEqual(consensus_events[0].decision, "approve")
        self.assertEqual(consensus_events[1].decision, "approve")
        self.assertIn(
            "report_deviation",
            [e.decision for e in state.history if e.stage_id == "republic_execute"],
        )

    def test_soviet_consensus_loop_guard_caps_report_deviation(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "soviet_party_state" / "soviet_consensus_loop.yaml"
        )
        vote_stage = next(s for s in spec.stages if s.id == "politburo_consensus")
        voters = list(vote_stage.consensus.voters if vote_stage.consensus else [])
        scripted = {
            "sovmin": ["next", "next", "next", "next"],
            "gosplan": ["next", "next", "next", "next"],
            "republic_exec": [
                "report_deviation",
                "report_deviation",
                "report_deviation",
                "report_deviation",
                "report_deviation",
            ],
            "supreme_soviet": ["next"],
        }
        scripted.update({v: ["yes", "yes", "yes", "yes"] for v in voters})
        rt = GovernanceRuntime(
            spec=spec,
            adapter=MockAdapter(scripted_decisions=scripted),
        )
        state = rt.run(
            task_id="SOV-VAR-LOOP-001",
            title="偏差回环上限",
            input_text="连续偏差上报不应无限回环",
            max_steps=40,
        )
        self.assertEqual(state.status, "done")

        republic_events = [e for e in state.history if e.stage_id == "republic_execute"]
        self.assertEqual([e.decision for e in republic_events], [
            "report_deviation",
            "report_deviation",
            "report_deviation",
            "next",
        ])
        self.assertIn("Loop guard forced", republic_events[-1].summary)
        self.assertEqual(republic_events[-1].meta.get("loop_guard", {}).get("max_count"), 3)

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
                    "prompt_template": "legacy prompt",
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
        spec = compile_spec(
            INSTITUTION_SPECS / "qinhan_junxian" / "qinhan_junxian.json"
        )
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

    def test_monitor_observer_reports_without_blocking_mainline(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "qinhan_junxian" / "qinhan_junxian.json"
        )
        adapter = MockAdapter(
            scripted_decisions={
                "yushi": ["alert", "ok", "alert", "ok"],
            }
        )
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="QH-MON-001",
            title="监察旁路测试",
            input_text="执行新税制并旁路监察",
            max_steps=12,
        )
        self.assertEqual(state.status, "done")
        self.assertEqual(
            [e.stage_id for e in state.history],
            ["huangdi_decree", "chengxiang_plan", "jun_dispatch", "xian_execute"],
        )

        for event in state.history:
            monitor = event.meta.get("monitor", [])
            self.assertTrue(any(m.get("type") == "heartbeat" for m in monitor))
            reports = [m for m in monitor if m.get("type") == "observer_report"]
            self.assertTrue(reports)
            self.assertEqual(reports[0].get("observer_agent"), "yushi")

        monitor_reports = state.shared_state.get("_monitor_reports", [])
        self.assertEqual(len(monitor_reports), 4)
        self.assertEqual(
            [str(x.get("observer_decision")) for x in monitor_reports],
            ["alert", "ok", "alert", "ok"],
        )

    def test_prompt_contains_topology_context(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "tang_sanshengliubu" / "tang_sanshengliubu.json"
        )
        rt = GovernanceRuntime(spec=spec, adapter=MockAdapter())
        stage = next(s for s in spec.stages if s.id == spec.entry_stage)
        task = TaskState(
            task_id="T-CTX",
            title="拓扑透传",
            input_text="测试",
            current_stage=spec.entry_stage,
            shared_state={"banned_terms": []},
        )
        prompt, _meta = rt._build_prompt(task, stage)
        self.assertIn("transitions", prompt)
        self.assertIn("allowed_decisions", prompt)

    def test_single_stage_includes_agent_profile(self) -> None:
        class CaptureAdapter:
            def __init__(self) -> None:
                self.messages: dict[str, list[str]] = {}
                self._lock = threading.Lock()

            def dispatch(
                self,
                runtime_id: str,
                message: str,
                timeout_sec: int = 300,
                retries: int = 1,
            ) -> AgentResult:
                del timeout_sec, retries
                with self._lock:
                    self.messages.setdefault(runtime_id, []).append(message)
                return AgentResult(decision="next", summary=f"capture:{runtime_id}")

        spec_obj = {
            "meta": {
                "id": "profile_demo",
                "name": "profile demo",
                "version": "0.1.0",
                "pattern": "pipeline",
            },
            "entry_stage": "plan",
            "agents": {
                "planner": {
                    "runtime_id": "planner",
                    "role": "planner",
                    "instructions": "PROFILE_MARKER_SINGLE_STAGE",
                }
            },
            "stages": [
                {
                    "id": "plan",
                    "kind": "planner",
                    "agent": "planner",
                    "prompt_template": "你是规划节点。任务:{title}",
                    "transitions": [{"decision": "next", "to": "done"}],
                },
                {"id": "done", "kind": "terminal"},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "profile_demo.json"
            path.write_text(json.dumps(spec_obj), encoding="utf-8")
            spec = compile_spec(path)

        adapter = CaptureAdapter()
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="P-001",
            title="profile test",
            input_text="profile",
            max_steps=8,
        )
        self.assertEqual(state.status, "done")
        msg = adapter.messages.get("planner", [""])[0]
        self.assertIn("[Agent Profile]", msg)
        self.assertIn("PROFILE_MARKER_SINGLE_STAGE", msg)

    def test_consensus_voters_receive_their_own_profile(self) -> None:
        class CaptureAdapter:
            def __init__(self) -> None:
                self.messages: dict[str, list[str]] = {}
                self._lock = threading.Lock()

            def dispatch(
                self,
                runtime_id: str,
                message: str,
                timeout_sec: int = 300,
                retries: int = 1,
            ) -> AgentResult:
                del timeout_sec, retries
                with self._lock:
                    self.messages.setdefault(runtime_id, []).append(message)

                decision = "yes" if runtime_id.startswith("citizen_") else "next"
                return AgentResult(decision=decision, summary=f"capture:{runtime_id}")

        spec = compile_spec(
            INSTITUTION_SPECS / "athens_democracy" / "athens_consensus.json"
        )
        adapter = CaptureAdapter()
        rt = GovernanceRuntime(spec=spec, adapter=adapter)
        state = rt.run(
            task_id="C-PROFILE-001",
            title="投票画像测试",
            input_text="是否通过提案",
            max_steps=10,
        )
        self.assertEqual(state.status, "done")
        for voter in ["citizen_01", "citizen_02", "citizen_03"]:
            runtime_id = spec.agents[voter].runtime_id
            instruction = spec.agents[voter].instructions
            msg = adapter.messages.get(runtime_id, [""])[0]
            self.assertIn("[Agent Profile]", msg)
            self.assertIn(instruction, msg)

    def test_trace_has_agent_rows_with_sequential_id(self) -> None:
        spec = compile_spec(
            INSTITUTION_SPECS / "egypt_pipeline" / "egypt_pipeline.json"
        )
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
        spec = compile_spec(
            INSTITUTION_SPECS / "athens_democracy" / "athens_consensus.json"
        )
        vote_stage = next(s for s in spec.stages if s.id == "ekklesia_vote")
        voters = list(vote_stage.consensus.voters if vote_stage.consensus else [])
        self.assertGreaterEqual(len(voters), 3)
        yes_voter = voters[0]
        no_voters = voters[1:]
        scripted = {"boule_planner_1": ["next"], yes_voter: ["yes"]}
        scripted.update({v: ["no"] for v in no_voters})
        adapter = MockAdapter(
            scripted_decisions=scripted
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
        self.assertEqual(len(agent_rows), 1 + len(voters))  # proposer + all voters
        self.assertEqual(
            [r["agent_trace"]["sequential_id"] for r in agent_rows],
            list(range(1, len(agent_rows) + 1)),
        )

    def test_soul_file_path_loaded_and_traced(self) -> None:
        old_cwd = Path.cwd()
        os.chdir(ROOT)
        try:
            with tempfile.TemporaryDirectory() as td:
                base = Path(td)
                (base / "souls").mkdir(parents=True, exist_ok=True)
                (base / "souls" / "planner.md").write_text(
                    "你是规划官。任务:{title}",
                    encoding="utf-8",
                )
                spec_path = base / "demo.yaml"
                spec_path.write_text(
                    """
meta:
  id: soul_demo
  name: Soul Demo
  version: "0.1.0"
  pattern: pipeline
entry_stage: plan
agents:
  planner:
    runtime_id: planner
stages:
  - id: plan
    kind: planner
    agent: planner
    description: 请先给出计划，再执行。
    soul_file_path: souls/planner.md
    transitions:
      - decision: next
        to: done
  - id: done
    kind: terminal
""",
                    encoding="utf-8",
                )
                spec = compile_spec(spec_path)
                trace_path = base / "trace.jsonl"
                rt = GovernanceRuntime(
                    spec=spec,
                    adapter=MockAdapter(),
                    store=JsonlStore(trace_path),
                )
                state = rt.run(
                    task_id="SOUL-001",
                    title="测试",
                    input_text="输入",
                    max_steps=4,
                )
                self.assertEqual(state.status, "done")
                rows = [
                    json.loads(line)
                    for line in trace_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                agent_rows = [r for r in rows if r.get("record_type") == "agent_trace"]
                self.assertEqual(len(agent_rows), 1)
                meta = agent_rows[0]["agent_trace"]["meta"]
                self.assertEqual(meta.get("prompt_mode"), "pattern_plus_soul")
                self.assertTrue(str(meta.get("soul_path", "")).endswith("souls/planner.md"))
                self.assertIn("pattern_soul_path", meta)
                self.assertIn("stage_description", meta)
                sections = meta.get("prompt_sections", [])
                self.assertIn("Prompt Precedence", sections)
                self.assertIn("Stage Objective", sections)
                self.assertIn("Pattern Rules", sections)
                self.assertIn("Institution SOP", sections)
        finally:
            os.chdir(old_cwd)

    def test_sop_violation_causes_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad_sop.json"
            path.write_text(
                json.dumps(
                    {
                        "meta": {
                            "id": "bad_sop",
                            "name": "Bad SOP",
                            "version": "0.1.0",
                            "pattern": "pipeline",
                        },
                        "entry_stage": "plan",
                        "agents": {"planner": {"runtime_id": "planner"}},
                        "stages": [
                            {
                                "id": "plan",
                                "kind": "planner",
                                "agent": "planner",
                                "prompt_template": "普通提示词",
                                "sop": {
                                    "required_patterns": ["MUST_CLI_MARKER"],
                                    "on_violation": "error",
                                },
                                "transitions": [{"decision": "next", "to": "done"}],
                            },
                            {"id": "done", "kind": "terminal"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            spec = compile_spec(path)
            rt = GovernanceRuntime(spec=spec, adapter=MockAdapter())
            state = rt.run(
                task_id="SOP-001",
                title="测试",
                input_text="输入",
                max_steps=4,
            )
            self.assertEqual(state.status, "error")
            self.assertEqual(state.history[0].decision, "error")
            sop_check = state.history[0].meta.get("sop_check", {})
            self.assertFalse(sop_check.get("passed", True))


if __name__ == "__main__":
    unittest.main()
