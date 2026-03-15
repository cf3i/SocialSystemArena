from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mas_engine.benchmark.multiagentbench import (
    MultiAgentBenchRunConfig,
    MultiAgentBenchGradeResult,
    MultiAgentBenchTask,
    _enforce_runtime_outcome,
    _grade_task,
    grade_multiagent_database,
    load_multiagent_tasks,
    select_multiagent_tasks,
)


def _make_task(scenario: str, task_id: int) -> MultiAgentBenchTask:
    return MultiAgentBenchTask(
        scenario=scenario,
        task_id=task_id,
        task_uid=f"{scenario}:{task_id:03d}",
        coordinate_mode="graph",
        relationships=[],
        agents=[],
        llm="demo-model",
        environment={"type": "Test", "max_iterations": 3},
        memory={"type": "BaseMemory"},
        metrics={},
        engine_planner={"initial_progress": "Starting"},
        output={"file_path": "result/out.jsonl"},
        prompt="demo prompt",
        output_format="json",
        labels=[],
        root_causes=[],
        number_of_labels_pred=0,
        source_file="/tmp/task.jsonl",
        raw_payload={},
    )


class MultiAgentBenchTests(unittest.TestCase):
    def test_load_multiagent_tasks_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data_dir = root / "multiagentbench" / "research"
            data_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "task_id": "1",
                "task": {
                    "content": "Draft a short research proposal.",
                    "output_format": "json",
                },
                "agents": [{"agent_id": "agent_1"}],
            }
            (data_dir / "research_main.jsonl").write_text(
                json.dumps(payload, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            tasks = load_multiagent_tasks(root, default_model="demo-model")

        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task.scenario, "research")
        self.assertEqual(task.task_uid, "research:001")
        self.assertEqual(task.llm, "demo-model")
        self.assertEqual(task.environment.get("type"), "Research")
        self.assertEqual(task.memory.get("type"), "BaseMemory")
        self.assertEqual(task.output.get("file_path"), "result/research_output.jsonl")

    def test_load_multiagent_tasks_tolerates_non_string_evaluate_llm(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data_dir = root / "multiagentbench" / "research"
            data_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "task_id": "2",
                "task": {
                    "content": "Draft a short research proposal.",
                    "output_format": "json",
                },
                "metrics": {
                    "evaluate_llm": {"provider": "x", "model": "y"},
                },
            }
            (data_dir / "research_main.jsonl").write_text(
                json.dumps(payload, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            tasks = load_multiagent_tasks(root, default_model="demo-model")

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].metrics.get("evaluate_llm"), "demo-model")

    def test_select_multiagent_tasks_with_aliases(self) -> None:
        tasks = [
            _make_task("research", 1),
            _make_task("database", 2),
            _make_task("coding", 3),
        ]
        selected = select_multiagent_tasks(
            tasks,
            scenario="research,database",
            suite="research:1,database:002",
        )
        self.assertEqual([t.task_uid for t in selected], ["research:001", "database:002"])

    def test_select_multiagent_tasks_rejects_unknown_scenario(self) -> None:
        with self.assertRaises(ValueError):
            select_multiagent_tasks([_make_task("research", 1)], scenario="foo", suite="all")

    def test_grade_multiagent_database(self) -> None:
        task = _make_task("database", 10)
        task.labels = ["LOCK_CONTENTION", "VACUUM"]
        task.root_causes = ["LOCK_CONTENTION", "VACUUM"]

        transcript = [
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Found LOCK_CONTENTION from EXPLAIN output."}],
                },
            }
        ]
        final_text = "Final diagnosis: LOCK_CONTENTION and VACUUM."

        grade = grade_multiagent_database(task, transcript, final_text)
        self.assertAlmostEqual(grade.score, 1.0)
        self.assertEqual(grade.breakdown.get("database.precision"), 1.0)
        self.assertEqual(grade.breakdown.get("database.recall"), 1.0)
        self.assertEqual(grade.breakdown.get("database.f1"), 1.0)

    def test_grade_task_research_fallback_when_judge_timeout(self) -> None:
        class _FailingAdapter:
            def dispatch(self, **kwargs):  # noqa: ANN003
                raise TimeoutError("timeout after 180s")

        task = _make_task("research", 1)
        transcript: list[dict[str, object]] = []
        final_summary = "toolCall used and final output produced with enough details."
        cfg = MultiAgentBenchRunConfig(mab_root=Path("."), model="demo-model")

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            out = _grade_task(
                task=task,
                transcript=transcript,
                final_summary=final_summary,
                workspace=workspace,
                adapter=_FailingAdapter(),  # type: ignore[arg-type]
                config=cfg,
                run_dir=run_dir,
                judge_agent_id="judge-test",
            )

        self.assertEqual(out.grading_type, "activity_automated_fallback")
        self.assertGreater(out.score, 0.0)
        self.assertIn("llm_judge_failed", out.notes)

    def test_grade_task_database_fallback_when_judge_timeout(self) -> None:
        class _FailingAdapter:
            def dispatch(self, **kwargs):  # noqa: ANN003
                raise TimeoutError("timeout after 180s")

        task = _make_task("database", 2)
        task.labels = ["LOCK_CONTENTION", "VACUUM"]
        task.root_causes = ["LOCK_CONTENTION", "VACUUM"]
        transcript: list[dict[str, object]] = []
        final_summary = "Detected LOCK_CONTENTION and VACUUM."
        cfg = MultiAgentBenchRunConfig(mab_root=Path("."), model="demo-model")

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            workspace = Path(td) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            out = _grade_task(
                task=task,
                transcript=transcript,
                final_summary=final_summary,
                workspace=workspace,
                adapter=_FailingAdapter(),  # type: ignore[arg-type]
                config=cfg,
                run_dir=run_dir,
                judge_agent_id="judge-test",
            )

        self.assertEqual(out.grading_type, "database_rule_fallback")
        self.assertAlmostEqual(out.score, 1.0)
        self.assertIn("llm_judge_failed", out.notes)

    def test_enforce_runtime_outcome_zeroes_score_on_error(self) -> None:
        grade = MultiAgentBenchGradeResult(
            task_uid="research:001",
            scenario="research",
            grading_type="llm_judge",
            score=1.0,
            max_score=1.0,
            breakdown={"task_completion": 1.0},
            notes="judge succeeded",
        )
        out = _enforce_runtime_outcome(
            grade=grade,
            runtime_status="error",
            runtime_error="dispatch timeout",
        )
        self.assertEqual(out.score, 0.0)
        self.assertEqual(out.grading_type, "llm_judge_runtime_guard")
        self.assertEqual(out.breakdown.get("runtime.ok"), 0.0)
        self.assertIn("runtime_not_done", out.notes)

    def test_enforce_runtime_outcome_keeps_score_on_done(self) -> None:
        grade = MultiAgentBenchGradeResult(
            task_uid="research:001",
            scenario="research",
            grading_type="activity_automated",
            score=0.7,
            max_score=1.0,
            breakdown={"activity.has_output": 1.0},
            notes="fallback automated grading",
        )
        out = _enforce_runtime_outcome(
            grade=grade,
            runtime_status="done",
            runtime_error="",
        )
        self.assertEqual(out.score, 0.7)
        self.assertEqual(out.grading_type, "activity_automated")


if __name__ == "__main__":
    unittest.main()
