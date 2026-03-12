"""Storage wrapper that writes trace rows and emits stream events."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..core.types import TaskEvent, TaskState
from ..storage.jsonl import JsonlStore
from .event_stream import InMemoryEventStream


@dataclass
class EventStreamStore:
    """Mirror runtime trace rows into an in-memory stream."""

    event_stream: InMemoryEventStream
    jsonl_store: JsonlStore | None = None

    @classmethod
    def with_trace_path(
        cls,
        event_stream: InMemoryEventStream,
        trace_path: str | Path | None,
    ) -> "EventStreamStore":
        store = JsonlStore(trace_path) if trace_path else None
        return cls(event_stream=event_stream, jsonl_store=store)

    def append_event(self, task: TaskState, event: TaskEvent) -> None:
        row = JsonlStore.build_event_row(task, event)
        if self.jsonl_store:
            self.jsonl_store.append_event(task, event)
        self.event_stream.publish(task.task_id, row)

    def append_agent_traces(
        self,
        task: TaskState,
        stage_index: int,
        stage_id: str,
        stage_kind: str,
        traces: list[dict],
    ) -> None:
        rows = JsonlStore.build_agent_rows(
            task=task,
            stage_index=stage_index,
            stage_id=stage_id,
            stage_kind=stage_kind,
            traces=traces,
        )
        if not rows:
            return

        if self.jsonl_store:
            self.jsonl_store.append_agent_traces(
                task=task,
                stage_index=stage_index,
                stage_id=stage_id,
                stage_kind=stage_kind,
                traces=traces,
            )
        for row in rows:
            self.event_stream.publish(task.task_id, row)

