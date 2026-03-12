"""Simple JSONL store for task traces."""

from __future__ import annotations

import json
from pathlib import Path

from ..core.types import TaskEvent, TaskState


class JsonlStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_event(self, task: TaskState, event: TaskEvent) -> None:
        row = {
            "record_type": "stage_event",
            "task_id": task.task_id,
            "title": task.title,
            "status": task.status,
            "current_stage": task.current_stage,
            "event": {
                "index": event.index,
                "stage_id": event.stage_id,
                "stage_kind": event.stage_kind,
                "agent": event.agent,
                "decision": event.decision,
                "summary": event.summary,
                "next_stage": event.next_stage,
                "meta": event.meta,
            },
            "shared_state": task.shared_state,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def append_agent_traces(
        self,
        task: TaskState,
        stage_index: int,
        stage_id: str,
        stage_kind: str,
        traces: list[dict],
    ) -> None:
        if not traces:
            return

        sorted_traces = sorted(
            traces,
            key=lambda item: int(item.get("sequential_id") or 0),
        )

        with self.path.open("a", encoding="utf-8") as f:
            for trace in sorted_traces:
                row = {
                    "record_type": "agent_trace",
                    "task_id": task.task_id,
                    "title": task.title,
                    "status": task.status,
                    "current_stage": task.current_stage,
                    "agent_trace": {
                        "stage_index": stage_index,
                        "stage_id": stage_id,
                        "stage_kind": stage_kind,
                        "sequential_id": trace.get("sequential_id"),
                        "agent_id": trace.get("agent_id"),
                        "runtime_id": trace.get("runtime_id"),
                        "decision": trace.get("decision"),
                        "summary": trace.get("summary"),
                        "raw_tail": trace.get("raw_tail", ""),
                        "updates": trace.get("updates", {}),
                        "meta": trace.get("meta", {}),
                    },
                    "shared_state": task.shared_state,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
