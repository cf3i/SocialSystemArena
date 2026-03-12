"""Tests for in-memory event stream and eventing store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mas_engine.core.types import TaskEvent, TaskState
from mas_engine.observability.event_stream import InMemoryEventStream
from mas_engine.observability.store import EventStreamStore


class EventStreamTests(unittest.TestCase):
    def test_publish_subscribe_and_replay(self) -> None:
        stream = InMemoryEventStream()
        stream.publish_lifecycle("T1", "task_started", {"stage": "s1"})
        stream.publish("T1", {"record_type": "stage_event", "status": "running"})

        self.assertEqual(
            [x["stream_seq"] for x in stream.list_events("T1")],
            [1, 2],
        )

        sub, close_sub = stream.subscribe("T1", since_seq=1)
        try:
            first = sub.get(timeout=1)
            self.assertEqual(first["stream_seq"], 2)

            stream.publish_lifecycle("T1", "task_finished", {"status": "done"})
            nxt = sub.get(timeout=1)
            self.assertEqual(nxt["stream_seq"], 3)
            self.assertEqual(nxt["event_type"], "task_finished")
        finally:
            close_sub()

    def test_event_stream_store_mirrors_rows(self) -> None:
        stream = InMemoryEventStream()
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "trace.jsonl"
            store = EventStreamStore.with_trace_path(stream, trace)

            task = TaskState(
                task_id="T2",
                title="title",
                input_text="input",
                current_stage="s1",
                status="running",
            )
            store.append_agent_traces(
                task=task,
                stage_index=0,
                stage_id="s1",
                stage_kind="planner",
                traces=[
                    {
                        "sequential_id": 1,
                        "agent_id": "a1",
                        "runtime_id": "a1",
                        "decision": "next",
                        "summary": "ok",
                        "raw_tail": "tail",
                        "updates": {},
                        "meta": {},
                    }
                ],
            )
            task.append_event(
                TaskEvent(
                    index=0,
                    stage_id="s1",
                    stage_kind="planner",
                    agent="a1",
                    decision="next",
                    summary="ok",
                    next_stage="s2",
                    meta={},
                )
            )
            store.append_event(task, task.history[-1])

            lines = [x for x in trace.read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(len(lines), 2)
            rows = stream.list_events("T2")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["record_type"], "agent_trace")
            self.assertEqual(rows[1]["record_type"], "stage_event")


if __name__ == "__main__":
    unittest.main()
