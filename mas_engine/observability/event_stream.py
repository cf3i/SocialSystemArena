"""Thread-safe in-memory event stream with replay and subscriptions."""

from __future__ import annotations

import queue
import threading
from datetime import datetime, timezone
from typing import Callable


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryEventStream:
    """Stores per-task ordered events and supports live subscribers."""

    def __init__(self, max_events_per_task: int = 5000):
        self.max_events_per_task = max(100, int(max_events_per_task))
        self._lock = threading.Lock()
        self._events: dict[str, list[dict]] = {}
        self._counters: dict[str, int] = {}
        self._subscribers: dict[str, list[queue.Queue]] = {}

    def publish(self, task_id: str, event: dict) -> dict:
        row = dict(event)
        row["task_id"] = task_id
        row.setdefault("ts", _utc_iso())

        with self._lock:
            seq = self._counters.get(task_id, 0) + 1
            self._counters[task_id] = seq
            row["stream_seq"] = seq

            arr = self._events.setdefault(task_id, [])
            arr.append(row)
            if len(arr) > self.max_events_per_task:
                del arr[: len(arr) - self.max_events_per_task]

            targets = list(self._subscribers.get(task_id, []))

        for q in targets:
            try:
                q.put_nowait(row)
            except queue.Full:
                # Drop oldest when subscriber queue is full.
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                try:
                    q.put_nowait(row)
                except queue.Full:
                    pass
        return row

    def publish_lifecycle(self, task_id: str, event_type: str, payload: dict | None = None) -> dict:
        return self.publish(
            task_id=task_id,
            event={
                "record_type": "lifecycle",
                "event_type": event_type,
                "payload": payload or {},
            },
        )

    def list_events(self, task_id: str, since_seq: int = 0, limit: int = 1000) -> list[dict]:
        with self._lock:
            arr = list(self._events.get(task_id, []))
        out = [e for e in arr if int(e.get("stream_seq", 0)) > int(since_seq)]
        if limit > 0:
            return out[:limit]
        return out

    def subscribe(
        self,
        task_id: str,
        since_seq: int = 0,
        max_queue_size: int = 2048,
    ) -> tuple[queue.Queue, Callable[[], None]]:
        q: queue.Queue = queue.Queue(maxsize=max(16, max_queue_size))
        with self._lock:
            backlog = [e for e in self._events.get(task_id, []) if int(e.get("stream_seq", 0)) > int(since_seq)]
            subs = self._subscribers.setdefault(task_id, [])
            subs.append(q)

        for row in backlog:
            try:
                q.put_nowait(row)
            except queue.Full:
                break

        def close() -> None:
            with self._lock:
                subs = self._subscribers.get(task_id, [])
                if q in subs:
                    subs.remove(q)

        return q, close

