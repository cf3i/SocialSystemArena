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
