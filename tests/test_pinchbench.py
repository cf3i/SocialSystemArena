from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mas_engine.benchmark.pinchbench import (
    PinchTask,
    PinchBenchRunConfig,
    _build_agent_id,
    _build_summary,
    _count_stage_tokens,
    _extract_pc_agent_loop_transcript,
    _infer_pc_tool_calls_from_text,
    _normalize_transcript_for_grading,
    _parse_pc_tool_calls,
    grade_pinch_task_automated,
    load_pinch_tasks,
    select_pinch_tasks,
)


class PinchBenchTests(unittest.TestCase):
    def test_load_pinch_task_markdown(self) -> None:
        task_md = """---
id: task_01_demo
name: Demo Task
category: demo
grading_type: automated
timeout_seconds: 60
workspace_files:
  - source: sample.txt
    dest: input/sample.txt
---
## Prompt

Write a file.

## Expected Behavior

Create out.txt.

## Grading Criteria

- [ ] out.txt exists

## Automated Checks

```python
def grade(transcript, workspace_path):
    from pathlib import Path
    p = Path(workspace_path) / "out.txt"
    return {"out_exists": 1.0 if p.exists() else 0.0}
```
"""
        with tempfile.TemporaryDirectory() as td:
            tasks_dir = Path(td) / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            (tasks_dir / "task_01_demo.md").write_text(task_md, encoding="utf-8")

            tasks = load_pinch_tasks(tasks_dir)

        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task.task_id, "task_01_demo")
        self.assertEqual(task.name, "Demo Task")
        self.assertEqual(task.grading_type, "automated")
        self.assertEqual(task.grading_criteria, ["out.txt exists"])
        self.assertIn("def grade", task.automated_checks)

    def test_select_automated_only(self) -> None:
        tasks = [
            PinchTask(
                task_id="task_a",
                name="A",
                category="c",
                grading_type="automated",
                timeout_seconds=120,
                workspace_files=[],
                prompt="p",
                expected_behavior="e",
                grading_criteria=[],
            ),
            PinchTask(
                task_id="task_b",
                name="B",
                category="c",
                grading_type="llm_judge",
                timeout_seconds=120,
                workspace_files=[],
                prompt="p",
                expected_behavior="e",
                grading_criteria=[],
            ),
        ]
        selected = select_pinch_tasks(tasks, "automated-only")
        self.assertEqual([x.task_id for x in selected], ["task_a"])

    def test_grade_automated(self) -> None:
        task = PinchTask(
            task_id="task_auto",
            name="Auto",
            category="demo",
            grading_type="automated",
            timeout_seconds=120,
            workspace_files=[],
            prompt="p",
            expected_behavior="e",
            grading_criteria=["out exists"],
            automated_checks="""
```python
def grade(transcript, workspace_path):
    from pathlib import Path
    p = Path(workspace_path) / "out.txt"
    return {"out_exists": 1.0 if p.exists() else 0.0}
```
""".strip(),
        )
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "out.txt").write_text("ok", encoding="utf-8")
            result = grade_pinch_task_automated(task, transcript=[], workspace_path=workspace)
        self.assertAlmostEqual(result.score, 1.0)
        self.assertEqual(result.breakdown.get("out_exists"), 1.0)

    def test_normalize_transcript_for_grading(self) -> None:
        transcript = [
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "toolCall",
                            "name": "read",
                            "arguments": {"path": "notes.md"},
                        }
                    ],
                },
            }
        ]
        out = _normalize_transcript_for_grading(transcript)
        item = out[0]["message"]["content"][0]
        self.assertEqual(item["name"], "read_file")
        self.assertEqual(item["params"]["files"], ["notes.md"])

    def test_build_agent_id_avoids_collision(self) -> None:
        model = "openai-codex/gpt-5.3-codex"
        a = _build_agent_id("mas-pinch-worker", model, "task-01-vizier")
        b = _build_agent_id("mas-pinch-worker", model, "task-01-nomarch")
        self.assertNotEqual(a, b)

    def test_parse_pc_agent_loop_tool_call_markdown(self) -> None:
        raw = (
            "🛠️ **正在调用工具:** `file_read`  📥**参数:**\n"
            "````text\n"
            "{\"path\":\"notes.md\",\"start\":1}\n"
            "````\n"
        )
        calls = _parse_pc_tool_calls(raw)
        self.assertEqual(len(calls), 1)
        name, params = calls[0]
        self.assertEqual(name, "read_file")
        self.assertEqual(params.get("files"), ["notes.md"])

    def test_extract_pc_agent_loop_transcript_from_history(self) -> None:
        class _Event:
            def __init__(self, raw_tail: str) -> None:
                self.meta = {"raw_tail": raw_tail}

        history = [
            _Event(
                "🛠️ **正在调用工具:** `file_read`  📥**参数:**\n"
                "````text\n"
                "{\"path\":\"notes.md\"}\n"
                "````\n"
            )
        ]
        transcript = _extract_pc_agent_loop_transcript(history)
        self.assertEqual(len(transcript), 1)
        item = transcript[0]["message"]["content"][0]
        self.assertEqual(item["type"], "toolCall")
        self.assertEqual(item["name"], "read_file")
        self.assertEqual(item["params"]["files"], ["notes.md"])

    def test_infer_pc_tool_calls_from_text(self) -> None:
        calls = _infer_pc_tool_calls_from_text(
            "已读取 notes.md，并写入 answer.txt 完成任务。"
        )
        self.assertIn(("read_file", {"files": ["notes.md"]}), calls)
        self.assertIn(("write_file", {"path": "answer.txt"}), calls)

    def test_count_stage_tokens_from_history_meta(self) -> None:
        class _Event:
            def __init__(self, meta) -> None:
                self.meta = meta

        history = [
            _Event({"tokens_input": 120, "tokens_output": 30, "tokens_total": 150}),
            _Event({"tokens_input": "80", "tokens_output": "20"}),
            _Event({"tokens_input": None, "tokens_output": "bad", "tokens_total": "bad"}),
        ]
        tokens_input, tokens_output, tokens_total = _count_stage_tokens(history)
        self.assertEqual(tokens_input, 200)
        self.assertEqual(tokens_output, 50)
        self.assertEqual(tokens_total, 250)

    def test_build_summary_includes_elapsed_and_token_totals(self) -> None:
        task = PinchTask(
            task_id="task_a",
            name="A",
            category="demo",
            grading_type="automated",
            timeout_seconds=120,
            workspace_files=[],
            prompt="p",
            expected_behavior="e",
            grading_criteria=[],
        )
        rows = [
            {
                "task_id": "task_a",
                "runtime_status": "done",
                "score": 0.6,
                "elapsed_sec": 12.34,
                "tokens_total": 300,
                "tokens_input": 220,
                "tokens_output": 80,
            },
            {
                "task_id": "task_a",
                "runtime_status": "done",
                "score": 0.8,
                "elapsed_sec": 7.66,
                "tokens_total": 120,
                "tokens_input": 90,
                "tokens_output": 30,
            },
        ]
        config = PinchBenchRunConfig(
            pinch_root=Path("."),
            model="demo-model",
        )
        summary = _build_summary(
            rows=rows,
            run_dir=Path("/tmp/pinchbench-demo"),
            config=config,
            selected=[task],
        )
        self.assertEqual(summary["total_elapsed_sec"], 20.0)
        self.assertEqual(summary["total_tokens"], 420)
        self.assertEqual(summary["total_tokens_input"], 310)
        self.assertEqual(summary["total_tokens_output"], 110)


if __name__ == "__main__":
    unittest.main()
