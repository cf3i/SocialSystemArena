"""Async task runner with event-stream publishing for dashboard usage."""

from __future__ import annotations

import json
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..adapters import MockAdapter, OpenClawAdapter, PcAgentLoopAdapter
from ..core.runtime import GovernanceRuntime
from ..spec.compiler import (
    compile_spec,
    compile_spec_obj,
    compile_spec_text,
    dump_spec_yaml,
    export_ir_json,
    load_spec_text,
)
from .event_stream import InMemoryEventStream
from .institutions import InstitutionRegistry
from .store import EventStreamStore


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskRecord:
    task_id: str
    title: str
    input_text: str
    spec_path: str
    institution_id: str
    institution_name: str
    spec_id: str
    spec_name: str
    spec_source: str
    adapter: str
    trace_out: str
    status: str
    created_at: str
    updated_at: str
    current_stage: str = ""
    steps: int = 0
    error: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    topology: dict[str, Any] = field(default_factory=dict)


class TaskRunManager:
    """Manage background runs and expose snapshots for API/UI."""

    def __init__(
        self,
        event_stream: InMemoryEventStream | None = None,
        trace_dir: str | Path = "traces",
        institutions_path: str | Path = "systems/institutions.yaml",
    ):
        self.event_stream = event_stream or InMemoryEventStream()
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)

        reg_path = Path(institutions_path).expanduser()
        if not reg_path.is_absolute():
            reg_path = (Path.cwd() / reg_path).resolve()
        else:
            reg_path = reg_path.resolve()
        reg_dir = reg_path.parent
        workspace_root = reg_dir.parent if reg_dir.name == "systems" else reg_dir
        self.registry = InstitutionRegistry(
            registry_path=reg_path,
            workspace_root=workspace_root,
        )

        self._lock = threading.Lock()
        self._tasks: dict[str, TaskRecord] = {}
        self._threads: dict[str, threading.Thread] = {}

    def start_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title", "")).strip()
        input_text = str(payload.get("input", payload.get("input_text", ""))).strip()
        if not title:
            raise ValueError("title is required")
        if not input_text:
            raise ValueError("input is required")

        resolved_spec = self._resolve_spec_from_payload(payload)
        spec = resolved_spec["spec"]
        topology = _build_topology(spec_ir=export_ir_json(spec))

        task_id = str(payload.get("task_id", "")).strip() or f"TASK-{uuid.uuid4().hex[:8]}"
        trace_out = str(payload.get("trace_out", "")).strip()
        if not trace_out:
            trace_out = str((self.trace_dir / f"{task_id}.jsonl").resolve())
        max_steps = int(payload.get("max_steps", 0) or 0)
        adapter = str(payload.get("adapter", "pc-agent-loop")).strip() or "pc-agent-loop"

        now = _utc_iso()
        record = TaskRecord(
            task_id=task_id,
            title=title,
            input_text=input_text,
            spec_path=str(resolved_spec.get("spec_path", "")),
            institution_id=str(resolved_spec.get("institution_id", "")),
            institution_name=str(resolved_spec.get("institution_name", "")),
            spec_id=str(resolved_spec.get("spec_id", "")),
            spec_name=str(resolved_spec.get("spec_name", "")),
            spec_source=str(resolved_spec.get("spec_source", "file")),
            adapter=adapter,
            trace_out=trace_out,
            status="queued",
            created_at=now,
            updated_at=now,
            current_stage=spec.entry_stage,
            topology=topology,
        )

        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"task_id already exists: {task_id}")
            self._tasks[task_id] = record

        self.event_stream.publish_lifecycle(
            task_id,
            "task_queued",
            {
                "spec_path": record.spec_path,
                "spec_source": record.spec_source,
                "institution_id": record.institution_id,
                "institution_name": record.institution_name,
                "spec_id": record.spec_id,
                "spec_name": record.spec_name,
                "adapter": record.adapter,
                "entry_stage": spec.entry_stage,
                "trace_out": trace_out,
            },
        )

        thread = threading.Thread(
            target=self._run_task,
            name=f"mas-task-{task_id}",
            daemon=True,
            args=(task_id, spec, payload, max_steps),
        )
        with self._lock:
            self._threads[task_id] = thread
        thread.start()

        return self.get_task(task_id)

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            ids = list(self._tasks.keys())
        rows = [self.get_task(tid) for tid in ids]
        rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return rows

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                raise KeyError(task_id)
            snapshot = {
                "task_id": record.task_id,
                "title": record.title,
                "input_text": record.input_text,
                "spec_path": record.spec_path,
                "institution_id": record.institution_id,
                "institution_name": record.institution_name,
                "spec_id": record.spec_id,
                "spec_name": record.spec_name,
                "spec_source": record.spec_source,
                "adapter": record.adapter,
                "trace_out": record.trace_out,
                "status": record.status,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "current_stage": record.current_stage,
                "steps": record.steps,
                "error": record.error,
                "result": dict(record.result),
            }

        progress = self._derive_progress(task_id)
        snapshot.update(progress)
        return snapshot

    def get_task_topology(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                raise KeyError(task_id)
            return dict(record.topology)

    def get_events(self, task_id: str, since_seq: int = 0, limit: int = 1000) -> list[dict]:
        return self.event_stream.list_events(task_id, since_seq=since_seq, limit=limit)

    def preview_topology(self, spec_path: str) -> dict[str, Any]:
        spec = compile_spec(spec_path)
        return _build_topology(export_ir_json(spec))

    def preview_topology_inline(self, spec_text: str, spec_format: str = "yaml") -> dict[str, Any]:
        spec = compile_spec_text(spec_text, fmt=spec_format)
        return _build_topology(export_ir_json(spec))

    def list_institutions(self) -> list[dict[str, Any]]:
        return self.registry.list_institutions()

    def get_institution(self, institution_id: str) -> dict[str, Any]:
        return self.registry.get_institution(institution_id)

    def get_spec(self, spec_id: str) -> dict[str, Any]:
        info = self.registry.get_spec(spec_id)
        path = Path(info["spec_path"])
        info = dict(info)
        info["exists"] = path.exists()
        return info

    def get_spec_text(self, spec_id: str) -> dict[str, Any]:
        info, text = self.registry.read_spec_text(spec_id)
        spec = compile_spec(info["spec_path"])
        ir = export_ir_json(spec)
        out = dict(info)
        out["spec_text"] = text
        out["spec_ir"] = ir
        out["topology"] = _build_topology(ir)
        return out

    def save_institution_spec(self, payload: dict[str, Any]) -> dict[str, Any]:
        spec_text = str(payload.get("spec_text", "")).strip()
        if not spec_text:
            raise ValueError("spec_text is required")

        spec_format = str(payload.get("spec_format", "yaml")).strip().lower() or "yaml"
        raw_obj = load_spec_text(spec_text, fmt=spec_format)
        compiled = compile_spec_obj(raw_obj)
        ir = export_ir_json(compiled)
        meta = ir.get("meta", {}) if isinstance(ir.get("meta"), dict) else {}

        inst_name_seed = str(payload.get("institution_name", "")).strip()
        inst_name_en_seed = str(payload.get("institution_name_en", "")).strip()
        spec_name_seed = str(payload.get("spec_name", "")).strip()
        spec_name_en_seed = str(payload.get("spec_name_en", "")).strip()
        meta_id_seed = str(meta.get("id", "")).strip()
        meta_name_seed = str(meta.get("name", "")).strip()

        institution_id = _normalize_entity_id(
            payload.get("institution_id", ""),
            fallback=(meta_id_seed or inst_name_seed),
            prefix="institution",
        )
        spec_id = _normalize_entity_id(
            payload.get("spec_id", ""),
            fallback=(meta_id_seed or spec_name_seed or institution_id),
            prefix="spec",
        )
        institution_name = (
            inst_name_seed
            or meta_name_seed
            or institution_id
        )
        spec_name = (
            spec_name_seed
            or meta_name_seed
            or spec_id
        )
        institution_description = str(payload.get("institution_description", "")).strip()
        institution_description_en = str(payload.get("institution_description_en", "")).strip()
        spec_description = str(payload.get("spec_description", "")).strip() or str(
            meta.get("description", "")
        ).strip()
        spec_description_en = str(payload.get("spec_description_en", "")).strip()
        spec_path = str(payload.get("spec_path", "")).strip() or None
        set_default = _as_bool(payload.get("set_default", True), default=True)
        canonical_text = dump_spec_yaml(raw_obj)

        saved = self.registry.upsert_institution_spec(
            institution_id=institution_id,
            institution_name=institution_name,
            institution_name_en=(inst_name_en_seed or institution_name),
            institution_description=institution_description,
            institution_description_en=(
                institution_description_en or institution_description
            ),
            spec_id=spec_id,
            spec_name=spec_name,
            spec_name_en=(spec_name_en_seed or spec_name),
            spec_description=spec_description,
            spec_description_en=(spec_description_en or spec_description),
            spec_path=spec_path,
            spec_text=canonical_text,
            set_default=set_default,
        )
        spec_info = self.get_spec_text(spec_id)
        return {
            "ok": True,
            "institution": saved["institution"],
            "spec": spec_info,
            "meta": meta,
            "topology": _build_topology(ir),
        }

    def validate_spec_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        resolved = self._resolve_spec_from_payload(payload)
        spec = resolved["spec"]
        ir = export_ir_json(spec)
        return {
            "ok": True,
            "meta": ir.get("meta", {}),
            "topology": _build_topology(ir),
            "spec_ir": ir,
            "resolved": {
                "spec_path": resolved.get("spec_path", ""),
                "institution_id": resolved.get("institution_id", ""),
                "institution_name": resolved.get("institution_name", ""),
                "spec_id": resolved.get("spec_id", ""),
                "spec_name": resolved.get("spec_name", ""),
                "spec_source": resolved.get("spec_source", "file"),
            },
        }

    def _run_task(self, task_id: str, spec: Any, payload: dict[str, Any], max_steps: int) -> None:
        self._touch_task(task_id, status="running")
        self.event_stream.publish_lifecycle(
            task_id,
            "task_started",
            {"entry_stage": spec.entry_stage},
        )

        trace_out = self.get_task(task_id)["trace_out"]
        store = EventStreamStore.with_trace_path(
            event_stream=self.event_stream,
            trace_path=trace_out,
        )

        try:
            adapter = self._build_adapter(payload)
            runtime = GovernanceRuntime(spec=spec, adapter=adapter, store=store)
            state = runtime.run(
                task_id=task_id,
                title=str(payload.get("title", "")),
                input_text=str(payload.get("input", payload.get("input_text", ""))),
                max_steps=(max_steps or None),
            )
            result = {
                "task_id": state.task_id,
                "status": state.status,
                "current_stage": state.current_stage,
                "steps": len(state.history),
                "history": [
                    {
                        "idx": e.index,
                        "stage": e.stage_id,
                        "decision": e.decision,
                        "next": e.next_stage,
                        "summary": e.summary,
                    }
                    for e in state.history
                ],
                "shared_state": state.shared_state,
            }
            self._touch_task(
                task_id,
                status=state.status,
                current_stage=state.current_stage,
                steps=len(state.history),
                result=result,
            )
            self.event_stream.publish_lifecycle(
                task_id,
                "task_finished",
                {
                    "status": state.status,
                    "current_stage": state.current_stage,
                    "steps": len(state.history),
                },
            )
        except Exception as exc:
            msg = str(exc)
            self._touch_task(task_id, status="error", error=msg)
            self.event_stream.publish_lifecycle(
                task_id,
                "task_error",
                {"message": msg},
            )
        finally:
            with self._lock:
                self._threads.pop(task_id, None)

    def _touch_task(self, task_id: str, **updates: Any) -> None:
        with self._lock:
            record = self._tasks[task_id]
            for k, v in updates.items():
                if hasattr(record, k):
                    setattr(record, k, v)
            record.updated_at = _utc_iso()

    def _derive_progress(self, task_id: str) -> dict[str, Any]:
        events = self.event_stream.list_events(task_id, since_seq=0, limit=0)
        if not events:
            return {}

        status = ""
        current_stage = ""
        steps = 0
        error = ""
        for row in events:
            kind = row.get("record_type")
            if kind == "stage_event":
                steps += 1
                current_stage = str(row.get("current_stage", current_stage))
                status = str(row.get("status", status))
            elif kind == "lifecycle":
                evt = str(row.get("event_type", ""))
                payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
                if evt == "task_started":
                    status = "running"
                elif evt == "task_finished":
                    status = str(payload.get("status", status or "done"))
                    current_stage = str(payload.get("current_stage", current_stage))
                elif evt == "task_error":
                    status = "error"
                    error = str(payload.get("message", ""))

        out: dict[str, Any] = {}
        if status:
            out["status"] = status
        if current_stage:
            out["current_stage"] = current_stage
        if steps:
            out["steps"] = steps
        if error:
            out["error"] = error
        return out

    def _resolve_spec_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        spec_inline = payload.get("spec_inline")
        spec_obj = payload.get("spec_obj")
        institution_id = str(payload.get("institution_id", "")).strip()
        spec_id = str(payload.get("spec_id", "")).strip()
        spec_path = str(payload.get("spec_path", payload.get("spec", ""))).strip()

        if isinstance(spec_obj, str) and spec_obj.strip():
            try:
                spec_obj = json.loads(spec_obj)
            except Exception as exc:
                raise ValueError(f"invalid spec_obj json: {exc}") from exc

        if isinstance(spec_obj, dict):
            spec = compile_spec_obj(spec_obj)
            return {
                "spec": spec,
                "spec_path": "<inline:object>",
                "institution_id": institution_id,
                "institution_name": self._institution_name_of(institution_id),
                "spec_id": spec_id,
                "spec_name": "",
                "spec_source": "inline_object",
            }

        if isinstance(spec_inline, str) and spec_inline.strip():
            fmt = str(payload.get("spec_format", "")).strip().lower()
            if not fmt:
                fmt = _guess_inline_format(spec_inline)
            spec = compile_spec_text(spec_inline, fmt=fmt)
            return {
                "spec": spec,
                "spec_path": f"<inline:{fmt}>",
                "institution_id": institution_id,
                "institution_name": self._institution_name_of(institution_id),
                "spec_id": spec_id,
                "spec_name": "",
                "spec_source": "inline_text",
            }

        resolved = self.registry.resolve_spec(
            institution_id=institution_id or None,
            spec_id=spec_id or None,
            spec_path=spec_path or None,
        )
        path = str(resolved.get("spec_path", "")).strip()
        if not path:
            raise ValueError("spec resolution failed: empty path")
        spec = compile_spec(path)
        return {
            "spec": spec,
            "spec_path": path,
            "institution_id": str(resolved.get("institution_id", institution_id)),
            "institution_name": str(resolved.get("institution_name", self._institution_name_of(institution_id))),
            "spec_id": str(resolved.get("spec_id", spec_id)),
            "spec_name": str(resolved.get("spec_name", "")),
            "spec_source": "file",
        }

    def _institution_name_of(self, institution_id: str) -> str:
        if not institution_id:
            return ""
        try:
            info = self.registry.get_institution(institution_id)
            return str(info.get("institution_name", ""))
        except Exception:
            return ""

    def _build_adapter(self, payload: dict[str, Any]) -> Any:
        adapter = str(payload.get("adapter", "pc-agent-loop")).strip() or "pc-agent-loop"

        if adapter == "openclaw":
            return OpenClawAdapter(
                executable=str(payload.get("openclaw_bin", "openclaw")),
                deliver_mode=str(payload.get("openclaw_deliver_mode", "auto")),
                project_dir=(
                    str(payload.get("openclaw_project_dir")).strip()
                    if payload.get("openclaw_project_dir")
                    else None
                ),
            )

        if adapter == "pc-agent-loop":
            llm_no = payload.get("pc_llm_no", None)
            if llm_no in ("", None):
                parsed_llm_no = None
            else:
                parsed_llm_no = int(llm_no)
            return PcAgentLoopAdapter(
                agent_root=str(payload.get("pc_agent_root", "third_party/pc-agent-loop")),
                shared_instance=bool(payload.get("pc_shared_instance", False)),
                llm_no=parsed_llm_no,
                mykey_path=(
                    str(payload.get("pc_mykey")).strip()
                    if payload.get("pc_mykey")
                    else None
                ),
            )

        mock_script = payload.get("mock_scripted", {})
        if isinstance(mock_script, str) and mock_script.strip():
            try:
                mock_script = json.loads(mock_script)
            except Exception as exc:
                raise ValueError(f"invalid mock_scripted json: {exc}") from exc
        if not isinstance(mock_script, dict):
            raise ValueError("mock_scripted must be an object")
        scripted = {
            str(k): [str(x) for x in v]
            for k, v in mock_script.items()
            if isinstance(v, list)
        }
        return MockAdapter(scripted_decisions=scripted)


def _build_topology(spec_ir: dict[str, Any]) -> dict[str, Any]:
    stages = spec_ir.get("stages", []) if isinstance(spec_ir.get("stages"), list) else []
    nodes = []
    edges = []
    for item in stages:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id", ""))
        if not sid:
            continue
        nodes.append(
            {
                "id": sid,
                "kind": str(item.get("kind", "")),
                "agent": item.get("agent"),
                "description": str(item.get("description", "")),
            }
        )
        transitions = item.get("transitions", [])
        if isinstance(transitions, list):
            for t in transitions:
                if not isinstance(t, dict):
                    continue
                edges.append(
                    {
                        "from": sid,
                        "decision": str(t.get("decision", "")),
                        "to": str(t.get("to", "")),
                    }
                )
    return {
        "meta": spec_ir.get("meta", {}),
        "entry_stage": spec_ir.get("entry_stage", ""),
        "nodes": nodes,
        "edges": edges,
        "agents": spec_ir.get("agents", {}),
    }


def _guess_inline_format(text: str) -> str:
    sample = text.lstrip()
    if sample.startswith("{") or sample.startswith("["):
        return "json"
    return "yaml"


def _normalize_entity_id(raw: Any, *, fallback: str, prefix: str) -> str:
    src = str(raw or "").strip()
    if not src:
        src = str(fallback or "").strip()
    src = src.lower().replace("-", "_")
    src = re.sub(r"\s+", "_", src)
    src = re.sub(r"[^a-z0-9_]", "", src)
    src = re.sub(r"_+", "_", src).strip("_")
    if src:
        return src
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _as_bool(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw != 0
    text = str(raw).strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default
